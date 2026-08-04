"""Task async yang dijalankan RQ worker: profiling -> rules -> entity resolution -> scoring."""
import io
import traceback
from datetime import datetime

from sqlalchemy import desc

from ..db import SessionLocal
from ..models import (
    ActivityLog,
    Alert,
    Anomaly,
    ClusterMember,
    DataConnection,
    Dataset,
    DatasetColumn,
    EntityCluster,
    GoldenRecord,
    Organization,
    Pipeline,
    QualityScoreHistory,
    RecordMatchScore,
    RuleResult,
    ValidationRule,
)
from ..services import storage
from ..services.anomaly import detect_anomalies
from ..services.db_connector import decrypt_password, fetch_dataframe
from ..services.entity_resolution import detect_roles, json_safe_record, resolve_entities
from ..services.loader import load_dataframe
from ..services.notifier import notify_alert, notify_dataset_processed
from ..services.pii import detect_pii
from ..services.profiling import profile_dataframe
from ..services.rule_engine import run_rule, suggest_builtin_rules
from ..services.scoring import compute_dimensions
from ..services.timeliness import compute_timeliness


def _log(db, org_id: int, message: str) -> None:
    db.add(ActivityLog(org_id=org_id, message=message))


def _refresh_anomalies(db, dataset, df, profiles) -> int:
    db.query(Anomaly).filter_by(dataset_id=dataset.id).delete()
    found = detect_anomalies(df, profiles)
    for a in found:
        db.add(Anomaly(dataset_id=dataset.id, **a))
    return len(found)


# turun >= poin ini dari run sebelumnya dianggap drift, bukan cuma fluktuasi wajar
DRIFT_SCORE_DROP = 10
DRIFT_COMPLETENESS_DROP = 10


def _apply_timeliness(dataset, score: dict, previous_run_at) -> dict | None:
    """Timeliness/Freshness Check (backlog #5): sisipkan dimensi timeliness ke skor bila
    dataset punya jadwal pemantauan aktif (F10) dan sudah pernah diproses sebelumnya,
    lalu hitung ulang skor keseluruhan. Kembalikan detail untuk alerting, atau None bila
    tidak relevan (dataset upload biasa / run pertama)."""
    detail = compute_timeliness(dataset.monitoring_enabled, dataset.monitoring_interval_minutes,
                                previous_run_at, datetime.utcnow())
    if detail is None:
        return None
    score["dimensions"]["timeliness"] = round(detail["score"] * 100, 1)
    values = list(score["dimensions"].values())
    score["overall"] = round(sum(values) / len(values), 1) if values else None
    return detail


def _check_and_alert(db, dataset, score: dict) -> None:
    """Panggil SEBELUM menyimpan QualityScoreHistory run ini, supaya history terakhir
    yang terbaca masih milik run sebelumnya (F10): alert threshold statis + drift
    (perubahan tajam dibanding run sebelumnya untuk dataset yang sama) + keterlambatan
    jadwal pemantauan (backlog #5)."""
    org = db.get(Organization, dataset.org_id)
    threshold = org.alert_threshold if org else 75

    def raise_alert(alert_type: str, severity: str, message: str) -> None:
        alert = Alert(org_id=dataset.org_id, dataset_id=dataset.id,
                      alert_type=alert_type, severity=severity, message=message)
        db.add(alert)
        if org is not None:
            try:
                notify_alert(org, alert)
            except Exception:  # noqa: BLE001 - notifikasi gagal tidak boleh gagalkan pipeline
                traceback.print_exc()

    prev = (db.query(QualityScoreHistory).filter_by(dataset_id=dataset.id)
            .order_by(desc(QualityScoreHistory.created_at)).first())
    timeliness = _apply_timeliness(dataset, score, prev.created_at if prev else None)
    overall = score["overall"]

    if overall is not None and overall < threshold:
        severity = "tinggi" if overall < threshold - 15 else "sedang"
        raise_alert("skor_rendah", severity,
                    f'Skor kualitas "{dataset.name}" ({overall}) di bawah threshold {threshold}')

    if timeliness is not None and not timeliness["on_time"]:
        severity = ("tinggi" if timeliness["minutes_since_previous"]
                    > timeliness["expected_minutes"] * 4 else "sedang")
        raise_alert("data_terlambat", severity,
                    f'Dataset "{dataset.name}" seharusnya diperbarui tiap '
                    f'{timeliness["expected_minutes"]} menit, tapi baru diperbarui lagi '
                    f'setelah {timeliness["minutes_since_previous"]:.0f} menit')

    if prev is None or overall is None:
        return

    drop = prev.score - overall
    if drop >= DRIFT_SCORE_DROP:
        severity = "tinggi" if drop >= DRIFT_SCORE_DROP * 2 else "sedang"
        raise_alert("drift_skor", severity,
                    f'Skor kualitas "{dataset.name}" turun tajam dari '
                    f"{prev.score} ke {overall} ({drop:.1f} poin) dibanding "
                    "pemeriksaan sebelumnya")

    prev_completeness = (prev.dimensions or {}).get("completeness")
    new_completeness = (score["dimensions"] or {}).get("completeness")
    if prev_completeness is not None and new_completeness is not None:
        completeness_drop = prev_completeness - new_completeness
        if completeness_drop >= DRIFT_COMPLETENESS_DROP:
            raise_alert("kolom_kosong_naik", "rendah",
                        f'Completeness "{dataset.name}" turun dari '
                        f"{prev_completeness} ke {new_completeness} — makin "
                        "banyak nilai kosong dibanding pemeriksaan sebelumnya")


def process_dataset(dataset_id: int, run_profiling: bool = True, run_rules: bool = True,
                    run_dedup: bool = True) -> None:
    """Jalankan tahap pipeline sesuai flag (dipakai Pipeline granular run — lihat
    run_pipeline di bawah). Default semua True mempertahankan perilaku lama (dipakai
    trigger upload/refresh_from_database yang selalu ingin pemrosesan penuh).
    run_rules turut menggerbang anomaly/PII/scoring karena keempatnya sama-sama
    bagian dari "validasi kualitas", berbeda konsep dari profiling statistik deskriptif
    murni atau entity resolution."""
    db = SessionLocal()
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        db.close()
        return
    try:
        dataset.status = "processing"
        db.commit()

        content = storage.get_object(dataset.storage_key)
        df = load_dataframe(content, dataset.filename)
        dataset.row_count = len(df)
        dataset.column_count = len(df.columns)

        # --- Profiling (F2) ---
        profiles = profile_dataframe(df) if (run_profiling or run_rules) else []
        if run_profiling:
            db.query(DatasetColumn).filter_by(dataset_id=dataset.id).delete()
            for prof in profiles:
                db.add(DatasetColumn(dataset_id=dataset.id, **prof))

        # --- Rule engine (F3): auto-attach rule bawaan saat run pertama ---
        rule_results: list = []
        validity_per_column: dict[str, list] = {}
        if run_rules:
            rules = db.query(ValidationRule).filter_by(dataset_id=dataset.id).all()
            if not rules:
                for suggestion in suggest_builtin_rules(df, profiles):
                    db.add(ValidationRule(dataset_id=dataset.id, source="builtin",
                                          enabled=True, **suggestion))
                db.commit()
                rules = db.query(ValidationRule).filter_by(dataset_id=dataset.id).all()

            db.query(RuleResult).filter_by(dataset_id=dataset.id).delete()
            for rule in rules:
                if not rule.enabled:
                    continue
                result = run_rule(df, rule.column_name, rule.rule_type, rule.params)
                db.add(RuleResult(rule_id=rule.id, dataset_id=dataset.id,
                                  checked=result["checked"], violations=result["violations"],
                                  sample_violations=result["samples"]))
                rule_results.append(result)
                validity_per_column.setdefault(rule.column_name, []).append(result)

        # --- Entity resolution (F5) + cluster (F6 data) ---
        new_cluster_count: int | None = None
        if run_dedup:
            db.query(RecordMatchScore).filter_by(dataset_id=dataset.id).delete()
            old_clusters = db.query(EntityCluster).filter_by(dataset_id=dataset.id).all()
            for cluster in old_clusters:
                db.query(ClusterMember).filter_by(cluster_id=cluster.id).delete()
                db.query(GoldenRecord).filter_by(cluster_id=cluster.id).delete()
                db.delete(cluster)
            db.commit()

            er = resolve_entities(df, dedup_config=dataset.dedup_config)
            roles = er["roles"]
            duplicate_records = 0
            for seq, cluster_data in enumerate(er["clusters"], start=1):
                cluster = EntityCluster(
                    dataset_id=dataset.id,
                    cluster_key=f"ec_{seq:05d}",
                    cohesion=cluster_data["cohesion"],
                    status="pending",
                    record_count=len(cluster_data["members"]),
                )
                db.add(cluster)
                db.flush()
                for member_idx in cluster_data["members"]:
                    db.add(ClusterMember(
                        cluster_id=cluster.id,
                        record_index=member_idx,
                        record_data=json_safe_record(cluster_data["records"][member_idx]),
                    ))
                for pair in cluster_data["pairs"]:
                    db.add(RecordMatchScore(
                        dataset_id=dataset.id, cluster_id=cluster.id,
                        record_a=pair["a"], record_b=pair["b"],
                        score=pair["score"], features=pair["parts"],
                    ))
                duplicate_records += len(cluster_data["members"])
            new_cluster_count = len(er["clusters"])
        else:
            roles = detect_roles([str(c) for c in df.columns])
            duplicate_records = (
                db.query(ClusterMember)
                .join(EntityCluster, ClusterMember.cluster_id == EntityCluster.id)
                .filter(EntityCluster.dataset_id == dataset.id,
                        EntityCluster.status.in_(("pending", "confirmed")))
                .count()
            )

        # --- Anomaly detection (F8) + PII detection (F11) + Scoring & scorecard ---
        anomaly_count = None
        pii_findings = None
        score = None
        if run_rules:
            anomaly_count = _refresh_anomalies(db, dataset, df, profiles)

            pii_findings = detect_pii(df, roles)
            dataset.pii_findings = pii_findings

            score = compute_dimensions(profiles, rule_results, duplicate_records, len(df))
            _check_and_alert(db, dataset, score)
            dataset.quality_score = score["overall"]
            dataset.dimensions = score["dimensions"]
            db.add(QualityScoreHistory(dataset_id=dataset.id, score=score["overall"] or 0,
                                       dimensions=score["dimensions"]))

            # update validity per kolom
            columns = db.query(DatasetColumn).filter_by(dataset_id=dataset.id).all()
            for column in columns:
                results = validity_per_column.get(column.name)
                if results:
                    checked = sum(r["checked"] for r in results)
                    violations = sum(r["violations"] for r in results)
                    column.validity = round(1 - violations / checked, 4) if checked else None

        dataset.status = "ready"
        dataset.error_message = None

        summary_parts = []
        if run_profiling:
            summary_parts.append(f"{len(profiles)} kolom di-profiling")
        if run_dedup:
            summary_parts.append(f"{new_cluster_count} cluster duplikat kandidat")
        if run_rules:
            summary_parts.append(f'skor {score["overall"]}, {anomaly_count} anomali, '
                                 f"{len(pii_findings)} kolom PII terdeteksi")
        if not summary_parts:
            summary_parts.append("tidak ada tahap aktif")
        _log(db, dataset.org_id,
             f'Dataset "{dataset.name}" selesai diproses — ' + "; ".join(summary_parts))
        db.commit()
        org = db.get(Organization, dataset.org_id)
        if org is not None:
            try:
                notify_dataset_processed(org, dataset)
            except Exception:  # noqa: BLE001
                traceback.print_exc()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        dataset = db.get(Dataset, dataset_id)
        if dataset:
            dataset.status = "error"
            dataset.error_message = f"Gagal re-validasi: {exc}"
            db.commit()
        dataset = db.get(Dataset, dataset_id)
        if dataset is not None:
            dataset.status = "error"
            dataset.error_message = f"{exc}"
            _log(db, dataset.org_id, f'Dataset "{dataset.name}" gagal diproses: {exc}')
            db.commit()
            org = db.get(Organization, dataset.org_id)
            if org is not None:
                try:
                    notify_dataset_processed(org, dataset)
                except Exception:  # noqa: BLE001
                    traceback.print_exc()
        traceback.print_exc()
    finally:
        db.close()


def run_pipeline(pipeline_id: int) -> None:
    """Entry point dipanggil manual ("Run Now") maupun terjadwal (rq-scheduler, lihat
    schedule_pipeline) untuk satu Pipeline. Menerjemahkan enable_profiling/enable_deduplication
    ke flag process_dataset lalu mencatat hasilnya balik ke baris Pipeline. run_rules cuma
    aktif saat KEDUA opsi menyala ("Jalankan Keduanya") — mode tunggal (profiling saja /
    dedup saja) sengaja jadi run ringan tanpa rule/anomaly/PII/scoring, sesuai nama opsinya."""
    db = SessionLocal()
    pipeline = db.get(Pipeline, pipeline_id)
    if pipeline is None:
        db.close()
        return
    pipeline.last_run_status = "running"
    pipeline.last_run_at = datetime.utcnow()
    pipeline.last_run_message = None
    db.commit()
    dataset_id = pipeline.dataset_id
    run_profiling = pipeline.enable_profiling
    run_dedup = pipeline.enable_deduplication
    db.close()

    process_dataset(dataset_id, run_profiling=run_profiling,
                    run_rules=run_profiling and run_dedup, run_dedup=run_dedup)

    db = SessionLocal()
    pipeline = db.get(Pipeline, pipeline_id)
    dataset = db.get(Dataset, dataset_id)
    if pipeline is not None:
        pipeline.last_run_at = datetime.utcnow()
        pipeline.last_run_status = "failed" if (dataset and dataset.status == "error") else "success"
        pipeline.last_run_message = dataset.error_message if dataset else None
        db.commit()
    db.close()


def _finish_pipeline_run(db, pipeline_id: int | None, status: str,
                         message: str | None = None) -> None:
    if pipeline_id is None:
        return
    pipeline = db.get(Pipeline, pipeline_id)
    if pipeline is not None:
        pipeline.last_run_status = status
        pipeline.last_run_at = datetime.utcnow()
        pipeline.last_run_message = message


def rerun_rules(dataset_id: int, pipeline_id: int | None = None) -> None:
    """Jalankan ulang validasi rule + hitung ulang skor tanpa mengulang entity resolution."""
    db = SessionLocal()
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        db.close()
        return
    try:
        dataset.status = "processing"
        db.commit()
        content = storage.get_object(dataset.storage_key)
        df = load_dataframe(content, dataset.filename)
        profiles = profile_dataframe(df)

        rules = db.query(ValidationRule).filter_by(dataset_id=dataset.id, enabled=True).all()
        db.query(RuleResult).filter_by(dataset_id=dataset.id).delete()
        rule_results = []
        validity_per_column: dict[str, list] = {}
        for rule in rules:
            result = run_rule(df, rule.column_name, rule.rule_type, rule.params)
            db.add(RuleResult(rule_id=rule.id, dataset_id=dataset.id,
                              checked=result["checked"], violations=result["violations"],
                              sample_violations=result["samples"]))
            rule_results.append(result)
            validity_per_column.setdefault(rule.column_name, []).append(result)

        _refresh_anomalies(db, dataset, df, profiles)

        from ..services.entity_resolution import detect_roles
        dataset.pii_findings = detect_pii(df, detect_roles([str(c) for c in df.columns]))

        duplicate_records = (
            db.query(ClusterMember)
            .join(EntityCluster, ClusterMember.cluster_id == EntityCluster.id)
            .filter(EntityCluster.dataset_id == dataset.id,
                    EntityCluster.status.in_(("pending", "confirmed")))
            .count()
        )
        score = compute_dimensions(profiles, rule_results, duplicate_records, len(df))
        _check_and_alert(db, dataset, score)
        dataset.quality_score = score["overall"]
        dataset.dimensions = score["dimensions"]
        db.add(QualityScoreHistory(dataset_id=dataset.id, score=score["overall"] or 0,
                                   dimensions=score["dimensions"]))

        columns = db.query(DatasetColumn).filter_by(dataset_id=dataset.id).all()
        for column in columns:
            results = validity_per_column.get(column.name)
            if results:
                checked = sum(r["checked"] for r in results)
                violations = sum(r["violations"] for r in results)
                column.validity = round(1 - violations / checked, 4) if checked else None

        dataset.status = "ready"
        dataset.error_message = None
        _finish_pipeline_run(db, pipeline_id, "success")
        _log(db, dataset.org_id,
             f'Validasi rule "{dataset.name}" dijalankan ulang — skor {score["overall"]}')
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        dataset = db.get(Dataset, dataset_id)
        if dataset:
            dataset.status = "error"
            dataset.error_message = f"Gagal re-validasi: {exc}"
            _finish_pipeline_run(db, pipeline_id, "failed", dataset.error_message)
            db.commit()
        traceback.print_exc()
    finally:
        db.close()


def refresh_dataset(dataset_id: int, pipeline_id: int | None = None) -> None:
    """Dispatcher source-aware (backlog #2) dipanggil scheduler & tombol 'Jalankan Ulang
    Validasi': dataset upload biasa cukup re-validasi (rerun_rules); dataset dari koneksi
    database menarik ulang data terbaru dari sumbernya dulu baru diproses penuh — supaya
    drift monitoring genuinely mendeteksi perubahan data, bukan cuma efek review manusia."""
    db = SessionLocal()
    dataset = db.get(Dataset, dataset_id)
    source_type = dataset.source_type if dataset else "upload"
    db.close()
    if source_type == "database":
        refresh_from_database(dataset_id, pipeline_id)
    else:
        rerun_rules(dataset_id, pipeline_id)


def refresh_from_database(dataset_id: int, pipeline_id: int | None = None) -> None:
    """Tarik ulang data terbaru dari koneksi database, timpa snapshot CSV di storage,
    lalu proses penuh lewat pipeline yang sama seperti dataset upload biasa."""
    db = SessionLocal()
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        db.close()
        return
    try:
        connection = db.get(DataConnection, dataset.connection_id)
        if connection is None:
            raise ValueError("Koneksi database sudah dihapus")
        df = fetch_dataframe(
            connection.db_type, connection.host, connection.port, connection.database,
            connection.username, decrypt_password(connection.password_encrypted),
            dataset.source_query,
        )
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        storage.put_object(dataset.storage_key, buf.getvalue().encode("utf-8"))
        _log(db, dataset.org_id,
             f'Data ditarik ulang dari koneksi "{connection.name}" untuk dataset '
             f'"{dataset.name}" ({len(df)} baris)')
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        dataset = db.get(Dataset, dataset_id)
        if dataset:
            dataset.status = "error"
            dataset.error_message = f"Gagal re-validasi: {exc}"
            db.commit()
        dataset = db.get(Dataset, dataset_id)
        if dataset is not None:
            dataset.status = "error"
            dataset.error_message = f"Gagal menarik data dari koneksi: {exc}"
            _finish_pipeline_run(db, pipeline_id, "failed", dataset.error_message)
            _log(db, dataset.org_id, f'Dataset "{dataset.name}" gagal menarik data: {exc}')
            db.commit()
        traceback.print_exc()
        db.close()
        return
    db.close()
    process_dataset(dataset_id)
    db = SessionLocal()
    dataset = db.get(Dataset, dataset_id)
    if dataset is not None and dataset.status == "error":
        _finish_pipeline_run(db, pipeline_id, "failed", dataset.error_message)
    else:
        _finish_pipeline_run(db, pipeline_id, "success")
    db.commit()
    db.close()
