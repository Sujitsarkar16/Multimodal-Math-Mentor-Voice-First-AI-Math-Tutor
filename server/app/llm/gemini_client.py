# app/llm/gemini_client.py

import google.generativeai as genai
from app.settings import settings

genai.configure(api_key=settings.GEMINI_API_KEY)


class GeminiClient:
    def __init__(self, model="gemini-2.5-flash"):
        self.model = genai.GenerativeModel(model)

    def generate(self, prompt: str):
        response = self.model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 1000
            }
        )
        return response.text.strip()
