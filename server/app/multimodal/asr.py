# app/multimodal/asr.py

import whisper
import re
from typing import Dict, Any, List, Tuple
from app.settings import settings


class ASRService:
    """
    Audio Speech Recognition service with advanced spoken math parsing.
    Converts spoken mathematical expressions into proper mathematical notation.
    
    Examples:
        "2 plus 2" → "2 + 2"
        "integral of log x" → "∫ log(x) dx"
        "x squared plus 3x minus 5" → "x² + 3x - 5"
        "the derivative of sine x" → "d/dx sin(x)"
    """
    
    def __init__(self, model_size: str = "small"):
        self.model = whisper.load_model(model_size)
        
        # Comprehensive spoken math replacements (order matters!)
        self.math_replacements = self._build_replacement_rules()

    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        try:
            result = self.model.transcribe(audio_path)
        except FileNotFoundError as e:
            raise RuntimeError(
                "FFmpeg is not installed or not found in system PATH. "
                "Please install FFmpeg to use audio transcription features."
            ) from e

        raw_text = result.get("text", "").strip()
        confidence = self._estimate_confidence(result)
        warnings = []

        # Enhanced math normalization
        normalized_text, normalization_warnings = self._normalize_math_text(raw_text)
        warnings.extend(normalization_warnings)

        needs_confirmation = confidence < settings.ASR_CONFIDENCE_THRESHOLD or len(warnings) > 0

        return {
            "raw_text": raw_text,
            "normalized_text": normalized_text,
            "text": normalized_text,  # Alias for compatibility
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

    def _build_replacement_rules(self) -> List[Tuple[str, str]]:
        """
        Build comprehensive replacement rules for spoken math.
        Order matters - more specific patterns should come first.
        """
        rules = []
        
        # === NUMBERS AND BASIC OPERATIONS ===
        # Spoken number words to digits
        number_words = {
            'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
            'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
            'ten': '10', 'eleven': '11', 'twelve': '12', 'thirteen': '13',
            'fourteen': '14', 'fifteen': '15', 'sixteen': '16', 'seventeen': '17',
            'eighteen': '18', 'nineteen': '19', 'twenty': '20', 'thirty': '30',
            'forty': '40', 'fifty': '50', 'sixty': '60', 'seventy': '70',
            'eighty': '80', 'ninety': '90', 'hundred': '100', 'thousand': '1000',
            'pi': 'π', 'infinity': '∞'
        }
        for word, num in number_words.items():
            rules.append((rf'\b{word}\b', num))
        
        # === CALCULUS OPERATIONS (most specific first) ===
        # Integrals
        rules.extend([
            (r'\b(?:the\s+)?integral\s+of\s+log(?:arithm)?\s*(?:of\s+)?(\w+)\b', r'∫ log(\1) d\1'),
            (r'\b(?:the\s+)?integral\s+of\s+ln\s*(?:of\s+)?(\w+)\b', r'∫ ln(\1) d\1'),
            (r'\b(?:the\s+)?integral\s+of\s+(\w+)\s+(?:squared|square)\b', r'∫ \1² d\1'),
            (r'\b(?:the\s+)?integral\s+of\s+(\w+)\s+cubed?\b', r'∫ \1³ d\1'),
            (r'\b(?:the\s+)?integral\s+of\s+sin(?:e)?\s*(\w+)\b', r'∫ sin(\1) d\1'),
            (r'\b(?:the\s+)?integral\s+of\s+cos(?:ine)?\s*(\w+)\b', r'∫ cos(\1) d\1'),
            (r'\b(?:the\s+)?integral\s+of\s+e\s*(?:to\s+the)?\s*(\w+)\b', r'∫ e^\1 d\1'),
            (r'\b(?:the\s+)?integral\s+of\s+(\w+)\b', r'∫ \1 dx'),
            (r'\b(?:the\s+)?definite\s+integral\s+from\s+(\w+)\s+to\s+(\w+)\s+of\s+(\w+)\b', r'∫_{\1}^{\2} \3 dx'),
            (r'\bintegrate\s+(\w+)\b', r'∫ \1 dx'),
        ])
        
        # Derivatives
        rules.extend([
            (r'\b(?:the\s+)?derivative\s+of\s+sin(?:e)?\s*(\w+)\b', r'd/d\1 sin(\1)'),
            (r'\b(?:the\s+)?derivative\s+of\s+cos(?:ine)?\s*(\w+)\b', r'd/d\1 cos(\1)'),
            (r'\b(?:the\s+)?derivative\s+of\s+(\w+)\s+(?:squared|square)\b', r'd/d\1 (\1²)'),
            (r'\b(?:the\s+)?derivative\s+of\s+(\w+)\s+cubed?\b', r'd/d\1 (\1³)'),
            (r'\b(?:the\s+)?derivative\s+of\s+e\s*(?:to\s+the)?\s*(\w+)\b', r'd/d\1 (e^\1)'),
            (r'\b(?:the\s+)?derivative\s+of\s+log(?:arithm)?\s*(?:of\s+)?(\w+)\b', r'd/d\1 log(\1)'),
            (r'\b(?:the\s+)?derivative\s+of\s+(\w+)\b', r'd/dx (\1)'),
            (r"\b(\w+)\s+prime\b", r"\1'"),
            (r"\b(\w+)\s+double\s+prime\b", r"\1''"),
            (r'\bd\s*(\w+)\s*(?:by|over)\s*d\s*(\w+)\b', r'd\1/d\2'),
        ])
        
        # Limits
        rules.extend([
            (r'\b(?:the\s+)?limit\s+(?:as\s+)?(\w+)\s+(?:approaches|goes\s+to|tends\s+to)\s+(\w+)\s+of\s+(\w+)\b', r'lim_{{\1→\2}} \3'),
            (r'\b(?:the\s+)?limit\s+of\s+(\w+)\s+(?:as\s+)?(\w+)\s+(?:approaches|goes\s+to)\s+(\w+)\b', r'lim_{{\2→\3}} \1'),
            (r'\blim\s+(\w+)\s+to\s+(\w+)\b', r'lim_{{\1→\2}}'),
        ])
        
        # Summation and Product
        rules.extend([
            (r'\b(?:the\s+)?sum(?:mation)?\s+(?:of\s+)?(\w+)\s+from\s+(\w+)\s+(?:equals?\s+)?(\w+)\s+to\s+(\w+)\b', r'∑_{\2=\3}^{\4} \1'),
            (r'\b(?:the\s+)?sum\s+of\s+(\w+)\b', r'∑ \1'),
            (r'\bsigma\s+(\w+)\b', r'∑ \1'),
            (r'\b(?:the\s+)?product\s+(?:of\s+)?(\w+)\s+from\s+(\w+)\s+(?:equals?\s+)?(\w+)\s+to\s+(\w+)\b', r'∏_{\2=\3}^{\4} \1'),
        ])
        
        # === EXPONENTS AND POWERS ===
        rules.extend([
            (r'\b(\w+)\s+to\s+the\s+power\s+(?:of\s+)?(\w+)\b', r'\1^\2'),
            (r'\b(\w+)\s+raised\s+to\s+(?:the\s+)?(?:power\s+)?(?:of\s+)?(\w+)\b', r'\1^\2'),
            (r'\b(\w+)\s+(?:squared|square)\b', r'\1²'),
            (r'\b(\w+)\s+cubed?\b', r'\1³'),
            (r'\bsquare\s+root\s+(?:of\s+)?(\w+)\b', r'√\1'),
            (r'\bcube\s+root\s+(?:of\s+)?(\w+)\b', r'∛\1'),
            (r'\b(\w+)th\s+root\s+(?:of\s+)?(\w+)\b', r'\1√\2'),
            (r'\bsqrt\s*(?:of\s+)?(\w+)\b', r'√\1'),
            (r'\be\s+to\s+(?:the\s+)?(\w+)\b', r'e^\1'),
            (r'\bexponential\s+(?:of\s+)?(\w+)\b', r'e^\1'),
        ])
        
        # === TRIGONOMETRIC FUNCTIONS ===
        rules.extend([
            (r'\bsine\s+(?:of\s+)?(\w+)\b', r'sin(\1)'),
            (r'\bcosine\s+(?:of\s+)?(\w+)\b', r'cos(\1)'),
            (r'\btangent\s+(?:of\s+)?(\w+)\b', r'tan(\1)'),
            (r'\bsecant\s+(?:of\s+)?(\w+)\b', r'sec(\1)'),
            (r'\bcosecant\s+(?:of\s+)?(\w+)\b', r'csc(\1)'),
            (r'\bcotangent\s+(?:of\s+)?(\w+)\b', r'cot(\1)'),
            (r'\barc\s*sine\s+(?:of\s+)?(\w+)\b', r'arcsin(\1)'),
            (r'\barc\s*cosine\s+(?:of\s+)?(\w+)\b', r'arccos(\1)'),
            (r'\barc\s*tangent\s+(?:of\s+)?(\w+)\b', r'arctan(\1)'),
            (r'\binverse\s+sine\s+(?:of\s+)?(\w+)\b', r'sin⁻¹(\1)'),
            (r'\binverse\s+cosine\s+(?:of\s+)?(\w+)\b', r'cos⁻¹(\1)'),
            (r'\binverse\s+tangent\s+(?:of\s+)?(\w+)\b', r'tan⁻¹(\1)'),
            (r'\bsin\s+(\w+)\b', r'sin(\1)'),
            (r'\bcos\s+(\w+)\b', r'cos(\1)'),
            (r'\btan\s+(\w+)\b', r'tan(\1)'),
        ])
        
        # === LOGARITHMS ===
        rules.extend([
            (r'\b(?:natural\s+)?log(?:arithm)?\s+(?:of\s+)?(\w+)\b', r'log(\1)'),
            (r'\bln\s+(?:of\s+)?(\w+)\b', r'ln(\1)'),
            (r'\blog\s+base\s+(\w+)\s+(?:of\s+)?(\w+)\b', r'log_{\1}(\2)'),
        ])
        
        # === BASIC ARITHMETIC OPERATIONS ===
        rules.extend([
            (r'\bplus\b', '+'),
            (r'\badded?\s+to\b', '+'),
            (r'\bminus\b', '-'),
            (r'\bsubtract(?:ed)?\s+(?:from|by)?\b', '-'),
            (r'\btimes\b', '×'),
            (r'\bmultiplied\s+by\b', '×'),
            (r'\binto\b', '×'),
            (r'\bdivided\s+by\b', '÷'),
            (r'\bover\b', '/'),
            (r'\bequals?\b', '='),
            (r'\bis\s+equal\s+to\b', '='),
            (r'\bnot\s+equal\s+to\b', '≠'),
            (r'\bless\s+than\s+or\s+equal\s+to\b', '≤'),
            (r'\bgreater\s+than\s+or\s+equal\s+to\b', '≥'),
            (r'\bless\s+than\b', '<'),
            (r'\bgreater\s+than\b', '>'),
            (r'\bapproximately\s+equal\s+to\b', '≈'),
            (r'\bplus\s+or\s+minus\b', '±'),
            (r'\bpercent\b', '%'),
            (r'\bfactorial\b', '!'),
            (r'\bmodulo\b', 'mod'),
        ])
        
        # === GREEK LETTERS ===
        greek_letters = {
            'alpha': 'α', 'beta': 'β', 'gamma': 'γ', 'delta': 'δ', 'epsilon': 'ε',
            'theta': 'θ', 'lambda': 'λ', 'mu': 'μ', 'sigma': 'σ', 'phi': 'φ',
            'omega': 'ω', 'rho': 'ρ', 'tau': 'τ'
        }
        for name, symbol in greek_letters.items():
            rules.append((rf'\b{name}\b', symbol))
        
        # === FRACTIONS ===
        rules.extend([
            (r'\b(\w+)\s+(?:over|divided\s+by)\s+(\w+)\b', r'\1/\2'),
            (r'\bhalf\b', '1/2'),
            (r'\bquarter\b', '1/4'),
            (r'\bthird\b', '1/3'),
        ])
        
        # === SPECIAL EXPRESSIONS ===
        rules.extend([
            (r'\babsolute\s+value\s+(?:of\s+)?(\w+)\b', r'|\1|'),
            (r'\bmodulus\s+(?:of\s+)?(\w+)\b', r'|\1|'),
            (r'\bopen\s+(?:parenthesis|bracket|paren)\b', '('),
            (r'\bclose\s+(?:parenthesis|bracket|paren)\b', ')'),
            (r'\bopen\s+square\s+bracket\b', '['),
            (r'\bclose\s+square\s+bracket\b', ']'),
        ])
        
        return rules

    def _normalize_math_text(self, text: str) -> Tuple[str, List[str]]:
        """
        Apply comprehensive math normalization to spoken text.
        Returns (normalized_text, list_of_warnings)
        """
        warnings = []
        normalized = text.lower().strip()
        
        # Apply all replacement rules
        for pattern, replacement in self.math_replacements:
            try:
                if re.search(pattern, normalized, re.IGNORECASE):
                    normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
            except re.error:
                continue
        
        # Detect remaining ambiguous phrases
        ambiguous_patterns = [
            (r'\bsomething\b', "ambiguous phrase: 'something'"),
            (r'\bapproximately\b', "phrase 'approximately' - may need specific value"),
            (r'\baround\b', "phrase 'around' - may need specific value"),
            (r'\bsome\s+value\b', "ambiguous phrase: 'some value'"),
            (r'\bpower\b', "word 'power' detected - verify exponent is correct"),
        ]
        
        for pattern, warning in ambiguous_patterns:
            if re.search(pattern, normalized, re.IGNORECASE):
                warnings.append(warning)
        
        # Clean up extra spaces
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Capitalize first letter for readability
        if normalized:
            normalized = normalized[0].upper() + normalized[1:]
        
        return normalized, warnings

