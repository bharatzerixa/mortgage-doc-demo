import json
from datetime import date
from services.llm_service import LLMService
from models.borrower import Borrower
from models.stip import Stip


class DocumentClassifier(LLMService):
    PROMPT_FILE = "document_classification.txt"

    def classify(self, file_bytes: bytes, media_type: str,
                 borrower: Borrower, stip_list: list[Stip]) -> dict:
        template = self.load_prompt(self.PROMPT_FILE)
        stip_view = [
            {
                "index": i,
                "name": s.name,
                "status": s.status,
                "notes": s.notes,
                # Pull through year/age constraints if present in the stip dict
                "accepted_years": getattr(s, "accepted_years", None),
                "accepted_doc_age_days": getattr(s, "accepted_doc_age_days", None),
            }
            for i, s in enumerate(stip_list)
        ]
        prompt = template.format(
            today=date.today().isoformat(),
            borrower=json.dumps(borrower.to_dict(), indent=2),
            stip_list=json.dumps(stip_view, indent=2),
            prior_year=date.today().year - 1,
            two_years_back=date.today().year - 2,
        )
        doc_block = self.build_doc_block(file_bytes, media_type)
        raw = self.call(
            [{
                "role": "user",
                "content": [doc_block, {"type": "text", "text": prompt}],
            }],
            max_tokens=1000,
        )
        return self.parse_json_response(raw)