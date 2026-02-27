from __future__ import annotations

import argparse
from pathlib import Path

from .db import connect_db, ensure_schema, list_trips, upsert_trip
from .email_parser import EmailParseError, parse_email_file


def ingest_directory(input_dir: Path, db_path: str) -> tuple[int, int]:
    conn = connect_db(db_path)
    ensure_schema(conn)

    success = 0
    errors = 0

    for email_file in sorted(input_dir.glob("*.txt")):
        try:
            record = parse_email_file(email_file)
            upsert_trip(conn, record)
            success += 1
        except EmailParseError as exc:
            errors += 1
            print(f"[ERRO] {exc}")

    conn.close()
    return success, errors


def print_trips(db_path: str) -> None:
    conn = connect_db(db_path)
    ensure_schema(conn)
    rows = list_trips(conn)

    if not rows:
        print("Nenhum registro encontrado.")
    else:
        for row in rows:
            print(
                " | ".join(
                    [
                        row["client"],
                        row["traveler"],
                        row["traveler_email"] or "-",
                        row["travel_date"],
                        row["destination"],
                        row["consultant"],
                        row["status"],
                        str(row["purchase_lead_days"]),
                        row["source_email"],
                    ]
                )
            )

    conn.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingestão de e-mails operacionais para viagens corporativas"
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        help="Diretório com e-mails .txt para processamento",
    )
    parser.add_argument(
        "--db-path",
        default="data/travel_ops.db",
        help="Caminho do banco SQLite",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Lista os registros após a ingestão",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists() or not input_dir.is_dir():
        raise SystemExit(f"Diretório inválido: {input_dir}")

    success, errors = ingest_directory(input_dir=input_dir, db_path=args.db_path)
    print(f"Processamento concluído. Sucesso: {success} | Erros: {errors}")

    if args.list:
        print_trips(db_path=args.db_path)


if __name__ == "__main__":
    main()
