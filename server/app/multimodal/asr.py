# app/multimodal/asr.py

import whisper
import re
from typing import Dict, Any


class ASRService:
    def __init__(self, model_size: str = "small"):
        self.model = whisper.load_model(model_size)

    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        try:
            result = self.model.transcribe(audio_path)
        except FileNotFoundError as e:
            # This usually happens if ffmpeg is not installed/found
            raise RuntimeError(
                "FFmpeg is not installed or not found in system PATH. "
                "Please install FFmpeg to use audio transcription features."
            ) from e


        raw_text = result.get("text", "").strip()
        confidence = self._estimate_confidence(result)
        warnings = []

        normalized_text, normalization_warnings = self._normalize_math_text(raw_text)
        warnings.extend(normalization_warnings)

        needs_confirmation = confidence < 0.75 or len(warnings) > 0

        return {
            "raw_text": raw_text,
            "normalized_text": normalized_text,
            "confidence": confidence,
            "warnings": warnings,
            "needs_confirmation": needs_confirmation
        }

    def _estimate_confidence(self, result: Dict[str, Any]) -> float:
        """
        Whisper doesn't give a single confidence score.
        We approximate using avg logprob and no_speech_prob.
        """
        segments = result.get("segments", [])
        if not segments:
            return 0.0

        avg_logprob = sum(s.get("avg_logprob", -1.0) for s in segments) / len(segments)
        no_speech_prob = sum(s.get("no_speech_prob", 0.0) for s in segments) / len(segments)

        # heuristic scaling
        confidence = max(0.0, min(1.0, 1 + avg_logprob - no_speech_prob))
        return round(confidence, 2)

    def _normalize_math_text(self, text: str):
        warnings = []

        replacements = {
            r"\bsquare\b": "^2",
            r"\bcube\b": "^3",
            r"\bsquare root of\b": "sqrt",
            r"\braised to the power of\b": "^",
            r"\braised to\b": "^",
            r"\binto\b": "*",
            r"\bdivided by\b": "/",
            r"\bequals\b": "=",
        }

        normalized = text.lower()

        for pattern, replacement in replacements.items():
            if re.search(pattern, normalized):
                normalized = re.sub(pattern, replacement, normalized)

        # detect ambiguous phrases
        ambiguous_phrases = [
            "something",
            "approximately",
            "around",
            "some value",
        ]

        for phrase in ambiguous_phrases:
            if phrase in normalized:
                warnings.append(f"ambiguous phrase detected: '{phrase}'")

        # detect spoken math without symbols
        if "power" in normalized and "^" not in normalized:
            warnings.append("possible exponent ambiguity")

        return normalized.strip(), warnings
