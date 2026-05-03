from utils.dates import parse_date_str


FREQ_MULTIPLIERS = {
    "weekly": 52 / 12,
    "biweekly": 26 / 12,
    "semimonthly": 2,
    "monthly": 1,
}


def estimate_monthly_income(extraction: dict):
    earnings = extraction.get("earnings") or {}
    pay_period = extraction.get("pay_period") or {}

    ytd = earnings.get("gross_pay_ytd")
    pay_date = parse_date_str(pay_period.get("pay_date"))

    if ytd and pay_date:
        months_elapsed = pay_date.month - 1 + (pay_date.day / 30)
        if months_elapsed >= 1:
            return ytd / months_elapsed, "YTD gross ÷ months elapsed"

    current = earnings.get("gross_pay_current_period")
    freq = pay_period.get("frequency")
    if current and freq in FREQ_MULTIPLIERS:
        return current * FREQ_MULTIPLIERS[freq], f"Current period × {freq} frequency"

    return None, "Insufficient data"