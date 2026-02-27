import tempfile
import unittest
from datetime import date

from src.travel_ops.db import connect_db, ensure_schema, upsert_trip
from src.travel_ops.models import TripRecord
from src.travel_ops.server import _query_kpis, _query_trips


class ServerQueryTests(unittest.TestCase):
    def test_query_trips_with_filters_and_kpis(self):
        with tempfile.NamedTemporaryFile(suffix=".db") as db_file:
            conn = connect_db(db_file.name)
            ensure_schema(conn)

            upsert_trip(
                conn,
                TripRecord(
                    client="ACME",
                    traveler="Pessoa 1",
                    travel_date=date(2026, 5, 10),
                    purchase_date=date(2026, 5, 1),
                    destination="Lima",
                    consultant="Ana",
                    status="Emitido",
                    source_email="a:1",
                ),
            )
            upsert_trip(
                conn,
                TripRecord(
                    client="Beta",
                    traveler="Pessoa 2",
                    travel_date=date(2026, 6, 10),
                    purchase_date=date(2026, 6, 8),
                    destination="Bogotá",
                    consultant="Carlos",
                    status="Aguardando aprovação",
                    source_email="b:1",
                ),
            )

            filtered = _query_trips(conn, {"client": "ACME", "status": "Emitido"})
            self.assertEqual(len(filtered), 1)
            self.assertEqual(filtered[0]["traveler"], "Pessoa 1")

            kpis = _query_kpis(conn)
            self.assertEqual(kpis["total_trips"], 2)
            self.assertIsNotNone(kpis["avg_purchase_lead_days"])

            conn.close()


if __name__ == "__main__":
    unittest.main()
