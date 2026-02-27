from __future__ import annotations

import argparse
import os
import smtplib
from dataclasses import dataclass
from datetime import date, datetime
from email.message import EmailMessage

from .db import connect_db, ensure_schema


@dataclass
class MessageJob:
    trip_id: int
    traveler: str
    traveler_email: str
    destination: str
    travel_date: str
    message_type: str
    subject: str
    body: str


def ensure_messaging_schema(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sent_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id INTEGER NOT NULL,
            message_type TEXT NOT NULL,
            scheduled_for TEXT NOT NULL,
            sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(trip_id, message_type, scheduled_for)
        )
        """
    )
    conn.commit()


def _build_content(message_type: str, traveler: str, destination: str, travel_date: str) -> tuple[str, str]:
    if message_type == "D-7_DESTINO":
        subject = f"Dicas para sua viagem a {destination}"
        body = (
            f"Olá {traveler},\n\n"
            f"Faltam 7 dias para sua viagem a {destination} ({travel_date}). "
            "Aqui vão dicas rápidas: documentos, clima, transporte local e moeda.\n\n"
            "Boa viagem!"
        )
        return subject, body

    if message_type == "D-2_CHECKIN":
        subject = "Lembrete de check-in"
        body = (
            f"Olá {traveler},\n\n"
            f"Sua viagem acontece em 2 dias ({travel_date}) para {destination}. "
            "Lembre-se de fazer check-in e revisar bagagem/documentos.\n\n"
            "Conte com nossa equipe!"
        )
        return subject, body

    subject = "Alerta pré-embarque (D-1)"
    body = (
        f"Olá {traveler},\n\n"
        f"Sua viagem para {destination} é amanhã ({travel_date}). "
        "Recomendamos chegar ao aeroporto com antecedência e validar documentos.\n\n"
        "Excelente viagem!"
    )
    return subject, body


def build_jobs(conn, reference_date: date) -> list[MessageJob]:
    rows = conn.execute(
        """
        SELECT id, traveler, traveler_email, destination, travel_date
        FROM trips
        WHERE traveler_email IS NOT NULL AND traveler_email <> ''
        """
    ).fetchall()

    jobs: list[MessageJob] = []
    for row in rows:
        travel_dt = datetime.strptime(row["travel_date"], "%Y-%m-%d").date()
        days_to_trip = (travel_dt - reference_date).days

        if days_to_trip == 7:
            message_type = "D-7_DESTINO"
        elif days_to_trip == 2:
            message_type = "D-2_CHECKIN"
        elif days_to_trip == 1:
            message_type = "D-1_ALERTA"
        else:
            continue

        already_sent = conn.execute(
            """
            SELECT 1 FROM sent_messages
            WHERE trip_id = ? AND message_type = ? AND scheduled_for = ?
            LIMIT 1
            """,
            (row["id"], message_type, reference_date.isoformat()),
        ).fetchone()
        if already_sent:
            continue

        subject, body = _build_content(
            message_type=message_type,
            traveler=row["traveler"],
            destination=row["destination"],
            travel_date=row["travel_date"],
        )

        jobs.append(
            MessageJob(
                trip_id=row["id"],
                traveler=row["traveler"],
                traveler_email=row["traveler_email"],
                destination=row["destination"],
                travel_date=row["travel_date"],
                message_type=message_type,
                subject=subject,
                body=body,
            )
        )

    return jobs


def _send_smtp(job: MessageJob) -> None:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    smtp_from = os.getenv("SMTP_FROM", smtp_user or "noreply@travelops.local")

    if not smtp_host or not smtp_user or not smtp_pass:
        raise RuntimeError(
            "Configure SMTP_HOST, SMTP_USER e SMTP_PASS para envio real"
        )

    msg = EmailMessage()
    msg["Subject"] = job.subject
    msg["From"] = smtp_from
    msg["To"] = job.traveler_email
    msg.set_content(job.body)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)


def run_messaging(db_path: str, reference_date: date, dry_run: bool = True) -> tuple[int, int]:
    conn = connect_db(db_path)
    ensure_schema(conn)
    ensure_messaging_schema(conn)

    jobs = build_jobs(conn, reference_date)

    sent = 0
    errors = 0

    for job in jobs:
        try:
            if dry_run:
                print(f"[DRY-RUN] {job.message_type} -> {job.traveler_email} | {job.subject}")
            else:
                _send_smtp(job)

            conn.execute(
                """
                INSERT OR IGNORE INTO sent_messages (trip_id, message_type, scheduled_for)
                VALUES (?, ?, ?)
                """,
                (job.trip_id, job.message_type, reference_date.isoformat()),
            )
            conn.commit()
            sent += 1
        except Exception as exc:  # noqa: BLE001
            errors += 1
            print(f"[ERRO] Falha ao enviar para {job.traveler_email}: {exc}")

    conn.close()
    return sent, errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Envia mensagens automáticas para viajantes (D-7, D-2, D-1)"
    )
    parser.add_argument("--db-path", default="data/travel_ops.db", help="Caminho do SQLite")
    parser.add_argument(
        "--reference-date",
        default=date.today().isoformat(),
        help="Data de referência no formato YYYY-MM-DD",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula envios sem enviar e-mail real",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    ref_date = datetime.strptime(args.reference_date, "%Y-%m-%d").date()
    sent, errors = run_messaging(args.db_path, reference_date=ref_date, dry_run=args.dry_run)
    print(f"Mensageria concluída. Enviados: {sent} | Erros: {errors}")


if __name__ == "__main__":
    main()
