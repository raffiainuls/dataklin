"""Notifikasi multi-channel (F10/F12, backlog #29): Email, Slack, Webhook generik.

Setiap channel independen dan gagal secara senyap (log ke stdout, tidak melempar) — kegagalan
mengirim notifikasi tidak boleh menggagalkan pipeline pemrosesan dataset. Channel yang belum
dikonfigurasi (URL/SMTP kosong) dilewati begitu saja, konsisten dengan pola services/llm.py.
"""
from __future__ import annotations

import smtplib
import traceback
from email.mime.text import MIMEText

import httpx

from ..config import settings
from ..models import Alert, Dataset, Organization


def _send_webhook(url: str, payload: dict) -> None:
    httpx.post(url, json=payload, timeout=10).raise_for_status()


def _send_slack(url: str, text: str) -> None:
    httpx.post(url, json={"text": text}, timeout=10).raise_for_status()


def _send_email(recipients: list[str], subject: str, body: str) -> None:
    if not settings.smtp_host:
        return
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = ", ".join(recipients)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.sendmail(settings.smtp_from, recipients, msg.as_string())


def _dispatch(org: Organization, subject: str, text: str, payload: dict) -> dict:
    """Kirim ke semua channel terkonfigurasi. Kembalikan status per-channel
    (None=tidak dikonfigurasi, True=berhasil, str=pesan error) — dipakai endpoint
    test-kirim untuk melaporkan jujur; pemanggil fire-and-forget (worker) boleh
    abaikan return value-nya."""
    results: dict[str, bool | str | None] = {"webhook": None, "slack": None, "email": None}
    if org.webhook_url:
        try:
            _send_webhook(org.webhook_url, payload)
            results["webhook"] = True
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            results["webhook"] = str(exc)
    if org.slack_webhook_url:
        try:
            _send_slack(org.slack_webhook_url, text)
            results["slack"] = True
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            results["slack"] = str(exc)
    if org.notify_emails:
        recipients = [e.strip() for e in org.notify_emails.split(",") if e.strip()]
        if recipients:
            try:
                _send_email(recipients, subject, text)
                results["email"] = True
            except Exception as exc:  # noqa: BLE001
                traceback.print_exc()
                results["email"] = str(exc)
    return results


def notify_alert(org: Organization, alert: Alert) -> dict:
    subject = f"[Dataklin] Alert {alert.severity}: {alert.alert_type}"
    text = f"{alert.message}\n\nTingkat: {alert.severity}"
    payload = {
        "event": "alert.created",
        "alert_type": alert.alert_type,
        "severity": alert.severity,
        "message": alert.message,
        "dataset_id": alert.dataset_id,
        "org_id": alert.org_id,
    }
    return _dispatch(org, subject, text, payload)


def notify_dataset_processed(org: Organization, dataset: Dataset) -> dict:
    if dataset.status == "ready":
        subject = f'[Dataklin] Dataset "{dataset.name}" selesai diproses'
        text = (f'Dataset "{dataset.name}" selesai diproses — skor kualitas '
                f"{dataset.quality_score}. Data siap diambil lewat clean.csv/dictionary.csv.")
    else:
        subject = f'[Dataklin] Dataset "{dataset.name}" gagal diproses'
        text = f'Dataset "{dataset.name}" gagal diproses: {dataset.error_message}'
    payload = {
        "event": "dataset.processed",
        "dataset_id": dataset.id,
        "name": dataset.name,
        "status": dataset.status,
        "quality_score": dataset.quality_score,
        "error_message": dataset.error_message,
    }
    return _dispatch(org, subject, text, payload)
