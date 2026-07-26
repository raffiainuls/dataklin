import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Dataset, DatasetColumn, EntityCluster, RuleResult, ValidationRule
from ..security import Actor, get_org_reader

router = APIRouter(tags=["scorecard"])

DIMENSION_LABELS = {
    "completeness": "Completeness",
    "validity": "Validity",
    "uniqueness": "Uniqueness",
    "consistency": "Consistency",
    "timeliness": "Timeliness",
}


def _scorecard_data(dataset_id: int, db: Session, user: Actor) -> dict:
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or dataset.org_id != user.org_id:
        raise HTTPException(404, "Dataset tidak ditemukan")
    columns = (db.query(DatasetColumn).filter_by(dataset_id=dataset.id)
               .order_by(DatasetColumn.position).all())
    rules = db.query(ValidationRule).filter_by(dataset_id=dataset.id).all()
    rule_map = {r.id: r for r in rules}
    results = db.query(RuleResult).filter_by(dataset_id=dataset.id).all()
    clusters = db.query(EntityCluster).filter_by(dataset_id=dataset.id).all()
    return {
        "dataset": dataset,
        "columns": columns,
        "rules": rule_map,
        "results": results,
        "clusters": clusters,
    }


@router.get("/datasets/{dataset_id}/scorecard")
def scorecard(dataset_id: int, db: Session = Depends(get_db),
              user: Actor = Depends(get_org_reader)):
    data = _scorecard_data(dataset_id, db, user)
    ds: Dataset = data["dataset"]
    return {
        "dataset": {"id": ds.id, "name": ds.name, "row_count": ds.row_count,
                    "column_count": ds.column_count, "quality_score": ds.quality_score,
                    "updated_at": ds.updated_at.isoformat()},
        "dimensions": ds.dimensions or {},
        "columns": [{
            "name": c.name, "type": c.inferred_type,
            "completeness": c.completeness, "uniqueness": c.uniqueness,
            "validity": c.validity, "consistency": c.consistency, "notes": c.notes,
        } for c in data["columns"]],
        "rule_results": [{
            "rule": (data["rules"][r.rule_id].description
                     if r.rule_id in data["rules"] else str(r.rule_id)),
            "column": (data["rules"][r.rule_id].column_name
                       if r.rule_id in data["rules"] else "-"),
            "checked": r.checked, "violations": r.violations,
        } for r in data["results"]],
        "clusters": {
            "total": len(data["clusters"]),
            "pending": sum(1 for c in data["clusters"] if c.status == "pending"),
            "confirmed": sum(1 for c in data["clusters"] if c.status == "confirmed"),
            "split": sum(1 for c in data["clusters"] if c.status == "split"),
        },
    }


@router.get("/datasets/{dataset_id}/scorecard.csv")
def scorecard_csv(dataset_id: int, db: Session = Depends(get_db),
                  user: Actor = Depends(get_org_reader)):
    data = _scorecard_data(dataset_id, db, user)
    ds: Dataset = data["dataset"]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Dataklin Data Quality Scorecard"])
    writer.writerow(["Dataset", ds.name])
    writer.writerow(["Dibuat", datetime.utcnow().isoformat()])
    writer.writerow(["Jumlah Baris", ds.row_count])
    writer.writerow(["Skor Keseluruhan", ds.quality_score])
    writer.writerow([])
    writer.writerow(["Dimensi", "Skor"])
    for key, value in (ds.dimensions or {}).items():
        writer.writerow([DIMENSION_LABELS.get(key, key), value])
    writer.writerow([])
    writer.writerow(["Kolom", "Tipe", "Completeness", "Uniqueness", "Validity",
                     "Consistency", "Catatan"])
    for c in data["columns"]:
        writer.writerow([c.name, c.inferred_type, c.completeness, c.uniqueness,
                         c.validity, c.consistency, c.notes])
    writer.writerow([])
    writer.writerow(["Rule", "Kolom", "Diperiksa", "Pelanggaran"])
    for r in data["results"]:
        rule = data["rules"].get(r.rule_id)
        writer.writerow([rule.description if rule else r.rule_id,
                         rule.column_name if rule else "-", r.checked, r.violations])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition":
                 f'attachment; filename="scorecard_{ds.id}.csv"'},
    )


@router.get("/datasets/{dataset_id}/scorecard.pdf")
def scorecard_pdf(dataset_id: int, db: Session = Depends(get_db),
                  user: Actor = Depends(get_org_reader)):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    data = _scorecard_data(dataset_id, db, user)
    ds: Dataset = data["dataset"]

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=f"Scorecard {ds.name}")
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("Dataklin — Data Quality Scorecard", styles["Title"]),
        Paragraph(f"Dataset: {ds.name} · {ds.row_count:,} baris · "
                  f"dibuat {datetime.utcnow():%d %b %Y %H:%M} UTC", styles["Normal"]),
        Spacer(1, 0.5 * cm),
        Paragraph(f"Skor Kualitas Keseluruhan: <b>{ds.quality_score}</b> / 100",
                  styles["Heading2"]),
        Spacer(1, 0.3 * cm),
    ]

    dim_rows = [["Dimensi", "Skor"]]
    for key, value in (ds.dimensions or {}).items():
        dim_rows.append([DIMENSION_LABELS.get(key, key), str(value)])
    col_rows = [["Kolom", "Tipe", "Lengkap", "Unik", "Valid", "Konsisten"]]
    for c in data["columns"]:
        def pct(v):
            return f"{round(v * 100)}%" if v is not None else "—"
        col_rows.append([c.name[:28], c.inferred_type, pct(c.completeness),
                         pct(c.uniqueness), pct(c.validity), pct(c.consistency)])

    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4f46e5")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
    ])
    for rows in (dim_rows, col_rows):
        table = Table(rows, hAlign="LEFT")
        table.setStyle(style)
        elements.extend([table, Spacer(1, 0.5 * cm)])

    cluster_info = data["clusters"]
    elements.append(Paragraph(
        f"Entity resolution: {len(cluster_info)} cluster duplikat kandidat "
        f"({sum(1 for c in cluster_info if c.status == 'confirmed')} dikonfirmasi, "
        f"{sum(1 for c in cluster_info if c.status == 'pending')} menunggu review).",
        styles["Normal"]))

    doc.build(elements)
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition":
                 f'attachment; filename="scorecard_{ds.id}.pdf"'},
    )
