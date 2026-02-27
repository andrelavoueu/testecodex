import tempfile
import unittest
from datetime import date

from src.travel_ops.db import connect_db, ensure_schema, upsert_trip
from src.travel_ops.models import TripRecord
from src.travel_ops.server import _query_kpis, _query_status_breakdown, _query_trips


class ServerQueryTests(unittest.TestCase):
    def test_query_trips_with_filters_kpis_and_pagination(self):
        with tempfile.NamedTemporaryFile(suffix=".db") as db_file:
            conn = connect_db(db_file.name)
            ensure_schema(conn)

            upsert_trip(
                conn,
                TripRecord(
                    client="ACME",
                    traveler="Pessoa 1",
                    traveler_email="p1@acme.com",
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
                    traveler_email="p2@beta.com",
                    travel_date=date(2026, 6, 10),
                    purchase_date=date(2026, 6, 8),
                    destination="Bogotá",
                    consultant="Carlos",
                    status="Aguardando aprovação",
                    source_email="b:1",
                ),
            )

            filtered = _query_trips(
                conn, {"client": "ACME", "status": "Emitido", "page": "1", "page_size": "1"}
            )
            self.assertEqual(filtered["total"], 1)
            self.assertEqual(len(filtered["items"]), 1)
            self.assertEqual(filtered["items"][0]["traveler"], "Pessoa 1")

            kpis = _query_kpis(conn)
            self.assertEqual(kpis["total_trips"], 2)
            self.assertIsNotNone(kpis["avg_purchase_lead_days"])

            breakdown = _query_status_breakdown(conn)
            self.assertEqual(len(breakdown), 2)

            conn.close()


if __name__ == "__main__":
    unittest.main()
