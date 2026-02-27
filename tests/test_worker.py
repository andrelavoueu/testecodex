import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from src.travel_ops.db import connect_db, ensure_schema, upsert_trip
from src.travel_ops.models import TripRecord
from src.travel_ops.worker import run_cycle


class WorkerTests(unittest.TestCase):
    def test_run_cycle_with_sync_error_and_messaging_dry_run(self):
        with tempfile.NamedTemporaryFile(suffix=".db") as db_file, tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False
        ) as cfg_file:
            cfg_path = Path(cfg_file.name)
            cfg_file.write(
                json.dumps(
                    {
                        "accounts": [
                            {
                                "email": "ops@example.com",
                                "imap_server": "imap.gmail.com",
                                "password_env": "MISSING_ENV_VAR",
                            }
                        ]
                    }
                )
            )
            cfg_file.flush()

            conn = connect_db(db_file.name)
            ensure_schema(conn)
            upsert_trip(
                conn,
                TripRecord(
                    client="Cliente",
                    traveler="Pessoa",
                    traveler_email="pessoa@cliente.com",
                    travel_date=date(2026, 5, 12),
                    purchase_date=date(2026, 5, 1),
                    destination="Lima",
                    consultant="Ana",
                    status="Emitido",
                    source_email="x:1",
                ),
            )
            conn.close()

            sync_success, sync_errors, msg_sent, msg_errors = run_cycle(
                config_path=str(cfg_path),
                db_path=db_file.name,
                messaging_dry_run=True,
                sync_dry_run=True,
                reference_date=date(2026, 5, 10),
            )

            self.assertEqual(sync_success, 0)
            self.assertEqual(sync_errors, 1)
            self.assertEqual(msg_sent, 1)
            self.assertEqual(msg_errors, 0)

            cfg_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
