# app/multimodal/ocr.py

import json
from PIL import Image
import google.generativeai as genai
from typing import Dict, Any
from app.settings import settings


genai.configure(api_key=settings.GEMINI_API_KEY)


OCR_PROMPT = """
You are an OCR engine specialized in mathematics.

STRICT RULES:
- DO NOT solve the problem
- DO NOT explain anything
- DO NOT infer missing values
- ONLY extract exactly what is visible in the image

TASK:
Extract all readable text from the image and convert mathematical notation to LaTeX format.

For mathematical expressions:
- Use LaTeX syntax: \\sum, \\frac{}{}, ^{} for superscripts, _{} for subscripts
- Preserve equation structure
- Use proper LaTeX delimiters: $ for inline math, $$ for display math
- Example: \\sum_{r=0}^{n} (-1)^r \\cdot ^nC_r \\left(\\frac{1}{r+p+1}\\right)

For regular text:
- Keep headings and titles as plain text
- Preserve line breaks between different elements

If handwriting or symbols are unclear:
- make your best guess
- mention it in "warnings"
- DO NOT leave empty - always provide your best interpretation

OUTPUT FORMAT (MUST BE VALID JSON):
{
  "raw_text": "<extracted text with LaTeX for math>",
  "confidence": <number between 0.7 and 1.0>,
  "warnings": ["<any issues or uncertainties>"],
  "layout": "inline_math | block_math | mixed",
  "needs_confirmation": <true if confidence < 0.85 or has warnings>
}

CRITICAL: Respond ONLY with valid JSON. No markdown, no code blocks, no extra text.
"""


class OCRService:
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required for OCR service")
        
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            generation_config={
                "temperature": 0.0,
                "max_output_tokens": 800,
            }
        )

    def extract_text(self, image_path: str) -> Dict[str, Any]:
        """Extract text from image with LaTeX formatting for math."""
        image = Image.open(image_path)

        response = self.model.generate_content(
            [OCR_PROMPT, image],
            stream=False
        )

        try:
            content = response.text.strip()
            
            # Remove markdown code blocks if present
            if content.startswith("```"):
                import re
                content = re.sub(r'^```(?:json)?\s*', '', content)
                content = re.sub(r'\s*```$', '', content)
                content = content.strip()
            
            parsed = json.loads(content)
            
            # Validate and normalize confidence
            confidence = float(parsed.get("confidence", 0.75))
            if confidence < 0.7:
                confidence = 0.75  # Reasonable default for readable math
            
            # Clean up the raw text - remove excessive newlines
            raw_text = parsed.get("raw_text", "").strip()
            # Replace multiple newlines with double newline
            import re
            raw_text = re.sub(r'\n{3,}', '\n\n', raw_text)
            
            result = {
                "raw_text": raw_text or "No text extracted",
                "text": raw_text or "No text extracted",  # Alias for compatibility
                "confidence": confidence,
                "warnings": parsed.get("warnings", []),
                "layout": parsed.get("layout", "mixed"),
                "needs_confirmation": parsed.get("needs_confirmation", confidence < 0.85)
            }
            
            return result
            
        except json.JSONDecodeError as e:
            # Try to extract text even if JSON parsing fails
            raw_response = response.text.strip()
            
            # If response looks like it has content but bad JSON
            if len(raw_response) > 10:
                return {
                    "raw_text": raw_response,
                    "text": raw_response,
                    "confidence": 0.75,  # Better default than 0.3
                    "warnings": ["JSON parsing failed - using raw response"],
                    "layout": "unknown",
                    "needs_confirmation": True
                }
            else:
                # Really bad response
                return {
                    "raw_text": "Failed to extract text from image",
                    "text": "Failed to extract text from image",
                    "confidence": 0.5,
                    "warnings": [f"OCR failed: {str(e)}"],
                    "layout": "unknown",
                    "needs_confirmation": True
                }
                
        except Exception as e:
            return {
                "raw_text": f"OCR error: {str(e)}",
                "text": f"OCR error: {str(e)}",
                "confidence": 0.5,
                "warnings": [str(e)],
                "layout": "unknown",
                "needs_confirmation": True
            }
