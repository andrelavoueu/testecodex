from __future__ import annotations

import argparse
import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .db import connect_db, ensure_schema


DASHBOARD_HTML = """<!doctype html>
<html lang='pt-BR'>
<head>
  <meta charset='utf-8'>
  <title>Dashboard Operacional de Viagens</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; }
    .kpis { display: flex; gap: 12px; margin-bottom: 16px; }
    .card { border: 1px solid #ddd; padding: 12px; border-radius: 8px; min-width: 200px; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
    th { background: #f7f7f7; }
  </style>
</head>
<body>
  <h1>Dashboard Operacional</h1>
  <div class='kpis'>
    <div class='card'>Total viagens: <strong id='total'>-</strong></div>
    <div class='card'>Média antecedência: <strong id='avg'>-</strong></div>
  </div>
  <table>
    <thead>
      <tr>
        <th>Cliente</th><th>Viajante</th><th>Data viagem</th><th>Destino</th><th>Consultor</th><th>Status</th><th>Antecedência</th>
      </tr>
    </thead>
    <tbody id='rows'></tbody>
  </table>

<script>
async function load() {
  const kpis = await fetch('/api/kpis').then(r => r.json());
  document.getElementById('total').textContent = kpis.total_trips;
  document.getElementById('avg').textContent = kpis.avg_purchase_lead_days ?? '-';

  const trips = await fetch('/api/trips').then(r => r.json());
  const rows = document.getElementById('rows');
  rows.innerHTML = '';
  trips.forEach(t => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${t.client}</td><td>${t.traveler}</td><td>${t.travel_date}</td><td>${t.destination}</td><td>${t.consultant}</td><td>${t.status}</td><td>${t.purchase_lead_days}</td>`;
    rows.appendChild(tr);
  });
}
load();
</script>
</body>
</html>
"""


def _query_trips(conn: sqlite3.Connection, filters: dict[str, str]) -> list[dict]:
    conditions = []
    params: list[str] = []

    if filters.get("client"):
        conditions.append("client = ?")
        params.append(filters["client"])
    if filters.get("consultant"):
        conditions.append("consultant = ?")
        params.append(filters["consultant"])
    if filters.get("status"):
        conditions.append("status = ?")
        params.append(filters["status"])
    if filters.get("start_date"):
        conditions.append("travel_date >= ?")
        params.append(filters["start_date"])
    if filters.get("end_date"):
        conditions.append("travel_date <= ?")
        params.append(filters["end_date"])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"""
        SELECT client, traveler, travel_date, destination, consultant, status, purchase_lead_days, source_email
        FROM trips
        {where_clause}
        ORDER BY travel_date ASC
    """
    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def _query_kpis(conn: sqlite3.Connection) -> dict:
    total = conn.execute("SELECT COUNT(*) AS c FROM trips").fetchone()["c"]
    avg = conn.execute("SELECT ROUND(AVG(purchase_lead_days), 2) AS a FROM trips").fetchone()["a"]
    return {"total_trips": total, "avg_purchase_lead_days": avg}


class DashboardHandler(BaseHTTPRequestHandler):
    db_path = "data/travel_ops.db"

    def _json_response(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        conn = connect_db(self.db_path)
        ensure_schema(conn)

        if parsed.path == "/" or parsed.path == "/dashboard":
            body = DASHBOARD_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            conn.close()
            return

        if parsed.path == "/health":
            self._json_response({"status": "ok"})
            conn.close()
            return

        if parsed.path == "/api/trips":
            query = parse_qs(parsed.query)
            filters = {k: v[0] for k, v in query.items() if v}
            trips = _query_trips(conn, filters)
            self._json_response(trips)
            conn.close()
            return

        if parsed.path == "/api/kpis":
            kpis = _query_kpis(conn)
            self._json_response(kpis)
            conn.close()
            return

        conn.close()
        self._json_response({"error": "not_found"}, status=404)


def run_server(db_path: str, host: str = "0.0.0.0", port: int = 8000) -> None:
    DashboardHandler.db_path = db_path
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    print(f"Servidor iniciado em http://{host}:{port}")
    server.serve_forever()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dashboard/API HTTP para viagens corporativas")
    parser.add_argument("--db-path", default="data/travel_ops.db", help="Caminho do banco SQLite")
    parser.add_argument("--host", default="0.0.0.0", help="Host do servidor")
    parser.add_argument("--port", type=int, default=8000, help="Porta do servidor")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    run_server(db_path=args.db_path, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
