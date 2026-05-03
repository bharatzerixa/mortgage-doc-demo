import json
from datetime import date
from services.llm_service import LLMService
from models.borrower import Borrower
from models.stip import Stip


class StipListGenerator(LLMService):
    PROMPT_FILE = "stip_generation.txt"

    def generate(self, borrower: Borrower) -> list[Stip]:
        template = self.load_prompt(self.PROMPT_FILE)
        today = date.today()
        prior_year = today.year - 1
        two_years_back = today.year - 2

        prompt = template.format(
            profile=json.dumps(borrower.to_dict(), indent=2),
            today=today.isoformat(),
            prior_year=prior_year,
            two_years_back=two_years_back,
        )
        raw = self.call(
            [{"role": "user", "content": prompt}],
            max_tokens=2000,
        )
        items = self.parse_json_response(raw)
        return [Stip.from_dict(item) for item in items]