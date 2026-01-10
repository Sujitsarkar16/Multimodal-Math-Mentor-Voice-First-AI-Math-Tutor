"""
Input Verifier Agent - Validates OCR/ASR extraction quality before parsing.
Checks confidence levels and triggers HITL when extraction quality is low.
This agent runs BEFORE the Parser to catch extraction issues early.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from app.agents.base import BaseAgent, AgentInput, AgentOutput
from app.settings import settings


class InputVerifierInput(AgentInput):
    """Input for the Input Verifier Agent."""
    extracted_text: str = Field(..., description="Text extracted from OCR/ASR")
    extraction_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence from OCR/ASR")
    input_type: str = Field(..., description="Source type: 'ocr', 'asr', or 'text'")
    warnings: List[str] = Field(default_factory=list, description="Warnings from extraction")
    needs_confirmation: bool = Field(default=False, description="Flag from extractor")


class InputVerifierOutput(AgentOutput):
    """Output from the Input Verifier Agent."""
    is_valid: bool = Field(..., description="Whether extraction quality is acceptable")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Verified confidence")
    requires_human_review: bool = Field(default=False, description="Needs HITL before proceeding")
    hitl_reason: Optional[str] = Field(None, description="Reason for HITL trigger")
    verified_text: str = Field(..., description="Text to proceed with (may be same as input)")
    quality_issues: List[str] = Field(default_factory=list, description="Identified quality issues")
    can_proceed: bool = Field(default=True, description="Whether pipeline can proceed")


class InputVerifierAgent(BaseAgent):
    """
    Verifies OCR/ASR extraction quality before sending to Parser.
    
    HITL Trigger Conditions:
    1. OCR confidence < 75%
    2. ASR confidence < 75%
    3. Extraction warnings present
    4. needs_confirmation flag set by extractor
    5. Text appears garbled or too short
    
    When HITL is triggered, the pipeline should pause and allow the user
    to review/edit the extracted text before proceeding to solve.
    """
    
    def __init__(self):
        super().__init__(name="input_verifier")
    
    def execute(self, input_data: InputVerifierInput) -> InputVerifierOutput:
        """
        Verify extraction quality and determine if HITL is needed.
        
        Args:
            input_data: InputVerifierInput with extracted text and metadata
            
        Returns:
            InputVerifierOutput with verification results
        """
        quality_issues = []
        hitl_reasons = []
        confidence = input_data.extraction_confidence
        
        # Direct text input doesn't need verification
        if input_data.input_type == "text":
            return InputVerifierOutput(
                is_valid=True,
                confidence=1.0,
                requires_human_review=False,
                hitl_reason=None,
                verified_text=input_data.extracted_text,
                quality_issues=[],
                can_proceed=True
            )
        
        # Check 1: OCR confidence threshold
        if input_data.input_type == "ocr":
            if confidence < settings.OCR_CONFIDENCE_THRESHOLD:
                hitl_reasons.append(
                    f"OCR confidence ({confidence:.0%}) is below threshold ({settings.OCR_CONFIDENCE_THRESHOLD:.0%})"
                )
                quality_issues.append("Low OCR confidence - text may be inaccurate")
        
        # Check 2: ASR confidence threshold
        if input_data.input_type == "asr":
            if confidence < settings.ASR_CONFIDENCE_THRESHOLD:
                hitl_reasons.append(
                    f"ASR confidence ({confidence:.0%}) is below threshold ({settings.ASR_CONFIDENCE_THRESHOLD:.0%})"
                )
                quality_issues.append("Low ASR confidence - transcription may be inaccurate")
        
        # Check 3: Warnings from extractor
        if input_data.warnings and len(input_data.warnings) > 0:
            hitl_reasons.append(f"Extraction warnings detected: {', '.join(input_data.warnings)}")
            quality_issues.extend(input_data.warnings)
        
        # Check 4: needs_confirmation flag from extractor
        if input_data.needs_confirmation:
            hitl_reasons.append("Extractor flagged content for confirmation")
            quality_issues.append("Content flagged for human review by extractor")
        
        # Check 5: Text quality heuristics
        text = input_data.extracted_text.strip()
        
        # Too short
        if len(text) < 10:
            hitl_reasons.append("Extracted text is too short (< 10 characters)")
            quality_issues.append("Very short extraction - may be incomplete")
        
        # Potential garbage characters (high ratio of special chars)
        if text:
            special_ratio = sum(1 for c in text if not c.isalnum() and not c.isspace()) / len(text)
            if special_ratio > 0.5:
                hitl_reasons.append("High ratio of special characters detected")
                quality_issues.append("Text may contain OCR artifacts or garbled content")
        
        # Determine final HITL status
        requires_hitl = len(hitl_reasons) > 0
        hitl_reason = "; ".join(hitl_reasons) if hitl_reasons else None
        
        # Log the verification result
        if requires_hitl:
            self.logger.warning(
                f"HITL triggered for {input_data.input_type} input: {hitl_reason}"
            )
        else:
            self.logger.info(
                f"Input verification passed for {input_data.input_type} "
                f"(confidence: {confidence:.0%})"
            )
        
        return InputVerifierOutput(
            is_valid=not requires_hitl,
            confidence=confidence,
            requires_human_review=requires_hitl,
            hitl_reason=hitl_reason,
            verified_text=input_data.extracted_text,
            quality_issues=quality_issues,
            can_proceed=not requires_hitl  # Block pipeline if HITL needed
        )
