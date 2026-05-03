from dataclasses import dataclass, asdict


@dataclass
class Borrower:
    name: str
    loan_purpose: str
    loan_amount: int
    property_address: str
    employment_type: str
    employer: str
    annual_income: int
    first_time_buyer: bool

    def to_dict(self):
        return asdict(self)