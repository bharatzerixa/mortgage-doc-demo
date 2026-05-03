from services.llm_service import LLMService


class PayStubExtractor(LLMService):
    PROMPT_FILE = "paystub_extraction.txt"

    def extract(self, file_bytes: bytes, media_type: str) -> dict:
        prompt = self.load_prompt(self.PROMPT_FILE)
        doc_block = self.build_doc_block(file_bytes, media_type)
        raw = self.call(
            [{
                "role": "user",
                "content": [doc_block, {"type": "text", "text": prompt}],
            }],
            max_tokens=2000,
        )
        return self.parse_json_response(raw)