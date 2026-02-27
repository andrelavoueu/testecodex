import tempfile
import unittest
from datetime import date

from src.travel_ops.db import connect_db, ensure_schema, upsert_trip
from src.travel_ops.messaging import build_jobs, ensure_messaging_schema
from src.travel_ops.models import TripRecord


class MessagingTests(unittest.TestCase):
    def test_build_jobs_for_d2(self):
        with tempfile.NamedTemporaryFile(suffix=".db") as db_file:
            conn = connect_db(db_file.name)
            ensure_schema(conn)
            ensure_messaging_schema(conn)

            upsert_trip(
                conn,
                TripRecord(
                    client="Cliente X",
                    traveler="Marina",
                    traveler_email="marina@x.com",
                    travel_date=date(2026, 5, 12),
                    purchase_date=date(2026, 5, 1),
                    destination="Santiago",
                    consultant="Ana",
                    status="Emitido",
                    source_email="msg:1",
                ),
            )

            jobs = build_jobs(conn, reference_date=date(2026, 5, 10))
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0].message_type, "D-2_CHECKIN")

            conn.close()


if __name__ == "__main__":
    unittest.main()
