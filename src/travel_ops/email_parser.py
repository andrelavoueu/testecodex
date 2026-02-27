from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .models import TripRecord

FIELD_ALIASES = {
    "cliente": "client",
    "viajante": "traveler",
    "email do viajante": "traveler_email",
    "e-mail do viajante": "traveler_email",
    "data da viagem": "travel_date",
    "destino": "destination",
    "consultor": "consultant",
    "consultor responsável": "consultant",
    "status": "status",
    "data da compra": "purchase_date",
}

REQUIRED_FIELDS = {
    "client",
    "traveler",
    "travel_date",
    "purchase_date",
    "destination",
    "consultant",
    "status",
}


class EmailParseError(ValueError):
    """Erro de parsing para e-mails operacionais."""


def _normalize_key(raw_key: str) -> str | None:
    return FIELD_ALIASES.get(raw_key.strip().lower())


def _parse_date(raw_date: str):
    return datetime.strptime(raw_date.strip(), "%Y-%m-%d").date()


def parse_email_content(content: str, source_email: str) -> TripRecord:
    parsed: dict[str, str] = {}

    for line in content.splitlines():
        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        normalized_key = _normalize_key(key)

        if normalized_key:
            parsed[normalized_key] = value.strip()

    missing = REQUIRED_FIELDS - parsed.keys()
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise EmailParseError(
            f"E-mail '{source_email}' sem campos obrigatórios: {missing_list}"
        )

    traveler_email = parsed.get("traveler_email") or None

    return TripRecord(
        client=parsed["client"],
        traveler=parsed["traveler"],
        traveler_email=traveler_email,
        travel_date=_parse_date(parsed["travel_date"]),
        purchase_date=_parse_date(parsed["purchase_date"]),
        destination=parsed["destination"],
        consultant=parsed["consultant"],
        status=parsed["status"],
        source_email=source_email,
    )


def parse_email_file(email_path: Path) -> TripRecord:
    content = email_path.read_text(encoding="utf-8")
    return parse_email_content(content=content, source_email=email_path.name)
