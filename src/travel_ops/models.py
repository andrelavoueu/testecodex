from dataclasses import dataclass
from datetime import date


@dataclass
class TripRecord:
    client: str
    traveler: str
    travel_date: date
    purchase_date: date
    destination: str
    consultant: str
    status: str
    source_email: str

    @property
    def purchase_lead_days(self) -> int:
        return (self.travel_date - self.purchase_date).days
