from __future__ import annotations

import argparse
import json
import os
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
    .kpis { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
    .card { border: 1px solid #ddd; padding: 12px; border-radius: 8px; min-width: 180px; }
    .filters { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
    th { background: #f7f7f7; }
  </style>
</head>
<body>
  <h1>Dashboard Operacional</h1>
  <div class='filters'>
    <input id='f-client' placeholder='Cliente'>
    <input id='f-consultant' placeholder='Consultor'>
    <input id='f-status' placeholder='Status'>
    <button onclick='load(1)'>Filtrar</button>
  </div>
  <div class='kpis'>
    <div class='card'>Total viagens: <strong id='total'>-</strong></div>
    <div class='card'>Média antecedência: <strong id='avg'>-</strong></div>
  </div>
  <table>
    <thead>
      <tr>
        <th>Cliente</th><th>Viajante</th><th>Email viajante</th><th>Data viagem</th><th>Destino</th><th>Consultor</th><th>Status</th><th>Antecedência</th>
      </tr>
    </thead>
    <tbody id='rows'></tbody>
  </table>
  <div style='margin-top: 10px'>
    <button onclick='prevPage()'>Anterior</button>
    <span id='page-info'>Página 1</span>
    <button onclick='nextPage()'>Próxima</button>
  </div>

<script>
let page = 1;
const pageSize = 10;

function paramsForPage(p){
  const q = new URLSearchParams();
  q.set('page', String(p));
  q.set('page_size', String(pageSize));
  const client = document.getElementById('f-client').value.trim();
  const consultant = document.getElementById('f-consultant').value.trim();
  const status = document.getElementById('f-status').value.trim();
  if (client) q.set('client', client);
  if (consultant) q.set('consultant', consultant);
  if (status) q.set('status', status);
  return q.toString();
}

async function load(p=1) {
  page = p;
  const kpis = await fetch('/api/kpis').then(r => r.json());
  document.getElementById('total').textContent = kpis.total_trips;
  document.getElementById('avg').textContent = kpis.avg_purchase_lead_days ?? '-';

  const trips = await fetch('/api/trips?' + paramsForPage(page)).then(r => r.json());
  const rows = document.getElementById('rows');
  rows.innerHTML = '';
  trips.items.forEach(t => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${t.client}</td><td>${t.traveler}</td><td>${t.traveler_email || '-'}</td><td>${t.travel_date}</td><td>${t.destination}</td><td>${t.consultant}</td><td>${t.status}</td><td>${t.purchase_lead_days}</td>`;
    rows.appendChild(tr);
  });
  document.getElementById('page-info').textContent = `Página ${trips.page} de ${trips.total_pages}`;
}

function nextPage(){ load(page + 1); }
function prevPage(){ if(page > 1) load(page - 1); }
load(1);
</script>
</body>
</html>
"""


def _parse_positive_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
        return parsed if parsed > 0 else default
    except ValueError:
        return default


def _query_trips(conn: sqlite3.Connection, filters: dict[str, str]) -> dict:
    conditions = []
    params: list[str] = []

    for field in ("client", "consultant", "status"):
        if filters.get(field):
            conditions.append(f"{field} = ?")
            params.append(filters[field])

    if filters.get("start_date"):
        conditions.append("travel_date >= ?")
        params.append(filters["start_date"])
    if filters.get("end_date"):
        conditions.append("travel_date <= ?")
        params.append(filters["end_date"])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    total = conn.execute(
        f"SELECT COUNT(*) AS c FROM trips {where_clause}",
        params,
    ).fetchone()["c"]

    page = _parse_positive_int(filters.get("page"), 1)
    page_size = min(_parse_positive_int(filters.get("page_size"), 20), 100)
    offset = (page - 1) * page_size

    rows = conn.execute(
        f"""
        SELECT client, traveler, traveler_email, travel_date, destination, consultant, status, purchase_lead_days, source_email
        FROM trips
        {where_clause}
        ORDER BY travel_date ASC
        LIMIT ? OFFSET ?
        """,
        [*params, page_size, offset],
    ).fetchall()

    total_pages = max((total + page_size - 1) // page_size, 1)
    if page > total_pages:
        page = total_pages

    return {
        "items": [dict(row) for row in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }


def _query_kpis(conn: sqlite3.Connection) -> dict:
    total = conn.execute("SELECT COUNT(*) AS c FROM trips").fetchone()["c"]
    avg = conn.execute("SELECT ROUND(AVG(purchase_lead_days), 2) AS a FROM trips").fetchone()["a"]
    return {"total_trips": total, "avg_purchase_lead_days": avg}


def _query_status_breakdown(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT status, COUNT(*) AS total
        FROM trips
        GROUP BY status
        ORDER BY total DESC, status ASC
        """
    ).fetchall()
    return [dict(row) for row in rows]


class DashboardHandler(BaseHTTPRequestHandler):
    db_path = "data/travel_ops.db"

    def _json_response(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _is_authorized(self, parsed_path: str) -> bool:
        api_key = os.getenv("TRAVEL_OPS_API_KEY")
        if not api_key:
            return True
        if parsed_path.startswith("/api/"):
            return self.headers.get("X-API-Key") == api_key
        return True

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)

        if not self._is_authorized(parsed.path):
            self._json_response({"error": "unauthorized"}, status=401)
            return

        conn = connect_db(self.db_path)
        ensure_schema(conn)

        try:
            if parsed.path == "/" or parsed.path == "/dashboard":
                body = DASHBOARD_HTML.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if parsed.path == "/health":
                self._json_response({"status": "ok"})
                return

            if parsed.path == "/api/trips":
                query = parse_qs(parsed.query)
                filters = {k: v[0] for k, v in query.items() if v}
                trips = _query_trips(conn, filters)
                self._json_response(trips)
                return

            if parsed.path == "/api/kpis":
                kpis = _query_kpis(conn)
                self._json_response(kpis)
                return

            if parsed.path == "/api/status-breakdown":
                breakdown = _query_status_breakdown(conn)
                self._json_response(breakdown)
                return

            self._json_response({"error": "not_found"}, status=404)
        finally:
            conn.close()


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
