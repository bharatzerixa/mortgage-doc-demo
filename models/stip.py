from dataclasses import dataclass, asdict
from typing import Optional, List


@dataclass
class Stip:
    name: str
    category: str
    notes: str = ""
    required: bool = True
    status: str = "missing"
    extraction: Optional[dict] = None
    doc_label: Optional[str] = None
    accepted_years: Optional[List[int]] = None
    accepted_doc_age_days: Optional[int] = None

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Stip":
        return cls(
            name=d.get("name", ""),
            category=d.get("category", "other"),
            notes=d.get("notes", ""),
            required=d.get("required", True),
            status=d.get("status", "missing"),
            extraction=d.get("extraction"),
            doc_label=d.get("doc_label"),
            accepted_years=d.get("accepted_years"),
            accepted_doc_age_days=d.get("accepted_doc_age_days"),
        )