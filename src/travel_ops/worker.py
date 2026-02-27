from __future__ import annotations

import argparse
import time
from datetime import date, datetime
from pathlib import Path

from .messaging import run_messaging
from .sync_inboxes import sync_from_config


def run_cycle(
    config_path: str,
    db_path: str,
    messaging_dry_run: bool,
    sync_dry_run: bool,
    reference_date: date | None = None,
) -> tuple[int, int, int, int]:
    ref = reference_date or date.today()

    sync_success, sync_errors = sync_from_config(
        config_path=Path(config_path),
        db_path=db_path,
        dry_run=sync_dry_run,
    )

    msg_sent, msg_errors = run_messaging(
        db_path=db_path,
        reference_date=ref,
        dry_run=messaging_dry_run,
    )

    return sync_success, sync_errors, msg_sent, msg_errors


def run_forever(
    config_path: str,
    db_path: str,
    interval_seconds: int,
    messaging_dry_run: bool,
    sync_dry_run: bool,
) -> None:
    while True:
        started = datetime.now().isoformat(timespec="seconds")
        print(f"[WORKER] Início do ciclo em {started}")

        sync_success, sync_errors, msg_sent, msg_errors = run_cycle(
            config_path=config_path,
            db_path=db_path,
            messaging_dry_run=messaging_dry_run,
            sync_dry_run=sync_dry_run,
        )

        finished = datetime.now().isoformat(timespec="seconds")
        print(
            "[WORKER] Fim do ciclo em "
            f"{finished} | sync_success={sync_success} sync_errors={sync_errors} "
            f"msg_sent={msg_sent} msg_errors={msg_errors}"
        )
        print(f"[WORKER] Aguardando {interval_seconds}s para próximo ciclo")
        time.sleep(interval_seconds)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Worker de produção: sincroniza caixas e dispara mensageria em ciclos"
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Arquivo JSON de contas IMAP",
    )
    parser.add_argument(
        "--db-path",
        default="data/travel_ops.db",
        help="Caminho do SQLite",
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=900,
        help="Intervalo entre ciclos (padrão: 900 = 15min)",
    )
    parser.add_argument(
        "--sync-dry-run",
        action="store_true",
        help="Processa sync sem persistir",
    )
    parser.add_argument(
        "--messaging-dry-run",
        action="store_true",
        help="Mensageria em modo simulação",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Executa apenas um ciclo e encerra",
    )
    parser.add_argument(
        "--reference-date",
        default=None,
        help="Data de referência YYYY-MM-DD para mensageria (opcional)",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.interval_seconds <= 0:
        raise SystemExit("--interval-seconds deve ser maior que zero")

    if args.once:
        ref = (
            datetime.strptime(args.reference_date, "%Y-%m-%d").date()
            if args.reference_date
            else date.today()
        )
        sync_success, sync_errors, msg_sent, msg_errors = run_cycle(
            config_path=args.config,
            db_path=args.db_path,
            messaging_dry_run=args.messaging_dry_run,
            sync_dry_run=args.sync_dry_run,
            reference_date=ref,
        )
        print(
            "[WORKER] Ciclo único finalizado | "
            f"sync_success={sync_success} sync_errors={sync_errors} "
            f"msg_sent={msg_sent} msg_errors={msg_errors}"
        )
        return

    run_forever(
        config_path=args.config,
        db_path=args.db_path,
        interval_seconds=args.interval_seconds,
        messaging_dry_run=args.messaging_dry_run,
        sync_dry_run=args.sync_dry_run,
    )


if __name__ == "__main__":
    main()
