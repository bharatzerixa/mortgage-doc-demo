from datetime import date, datetime
from typing import Optional


def parse_date_str(s: Optional[str]):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def freshness_status(pay_date_str: Optional[str], today: Optional[date] = None):
    """Fannie Mae: pay stubs must be dated within 30 days of application."""
    today = today or date.today()
    pd = parse_date_str(pay_date_str)
    if not pd:
        return ("unknown", "Pay date could not be determined")
    days_old = (today - pd).days
    if days_old < 0:
        return ("unknown", "Pay date is in the future — verify document")
    if days_old <= 30:
        return ("current",
                f"Current — {days_old} days old (≤30 days, meets Fannie Mae freshness)")
    if days_old <= 60:
        return ("borderline",
                f"Borderline — {days_old} days old (>30 days, may require updated doc)")
    return ("stale",
            f"Stale — {days_old} days old (well beyond 30-day window)")