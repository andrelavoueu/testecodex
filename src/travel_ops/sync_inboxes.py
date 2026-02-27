from __future__ import annotations

import argparse
import json
from pathlib import Path

from .db import connect_db, ensure_schema, upsert_trip
from .email_parser import EmailParseError, parse_email_content
from .email_sources import ImapEmailSource


def sync_from_config(config_path: Path, db_path: str, dry_run: bool = False) -> tuple[int, int]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    accounts = config.get("accounts", [])

    conn = connect_db(db_path)
    ensure_schema(conn)

    success = 0
    errors = 0

    for account in accounts:
        source = ImapEmailSource(
            account_email=account["email"],
            imap_server=account["imap_server"],
            password_env=account["password_env"],
            folder=account.get("folder", "INBOX"),
            search_criteria=account.get("search_criteria", "UNSEEN"),
        )

        try:
            messages = source.fetch_messages()
        except Exception as exc:  # noqa: BLE001
            errors += 1
            print(f"[ERRO] Conta {account.get('email')}: {exc}")
            continue

        for msg in messages:
            try:
                record = parse_email_content(content=msg.body, source_email=msg.source_id)
                if not dry_run:
                    upsert_trip(conn, record)
                success += 1
            except EmailParseError as exc:
                errors += 1
                print(f"[ERRO] {exc}")

    conn.close()
    return success, errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sincroniza múltiplas contas de e-mail operacionais (IMAP)"
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Arquivo JSON de configuração das contas IMAP",
    )
    parser.add_argument(
        "--db-path",
        default="data/travel_ops.db",
        help="Caminho do banco SQLite",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Processa e valida sem salvar no banco",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists() or not config_path.is_file():
        raise SystemExit(f"Arquivo de configuração inválido: {config_path}")

    success, errors = sync_from_config(
        config_path=config_path,
        db_path=args.db_path,
        dry_run=args.dry_run,
    )
    print(f"Sincronização concluída. Sucesso: {success} | Erros: {errors}")


if __name__ == "__main__":
    main()
