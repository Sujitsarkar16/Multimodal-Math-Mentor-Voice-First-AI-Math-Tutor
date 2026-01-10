"""
Parser Agent - Converts raw input into structured problem representation.
Uses LLM to extract problem components, variables, and constraints.
"""

from app.agents.base import BaseAgent
from app.agents.models import ParserInput, ParserOutput
from app.llm.client import get_llm_client
from app.core.exceptions import ParsingError
from app.settings import settings


class ParserAgent(BaseAgent):
    """
    Parses raw problem text into structured format.
    Identifies topic, variables, constraints, and ambiguities.
    Uses careful analysis to ensure nothing is missed.
    """
    
    SYSTEM_PROMPT = """You are an expert mathematical problem analyst. Your critical role is to thoroughly understand and structure problems BEFORE they are solved.

## 2-STEP ANALYSIS PROCESS:

### STEP 1: COMPREHENSION
Read the problem carefully and identify:
- What is the core question being asked?
- What type of mathematical problem is this?
- What information is explicitly given?
- What information is implied or assumed?

### STEP 2: EXTRACTION
Systematically extract:
- All variables (known and unknown)
- All constraints and conditions
- Units of measurement (if any)
- Any ambiguities or missing information

## GUIDELINES:
- Do NOT attempt to solve the problem
- Be precise with mathematical terminology
- Identify the specific mathematical domain (algebra, calculus, geometry, etc.)
- Extract numerical values AND their units
- Note any implicit assumptions
- Flag unclear or ambiguous statements
- Consider what additional information might be needed

## COMMON PROBLEM TYPES TO IDENTIFY:
- Algebra: equations, inequalities, systems of equations
- Calculus: derivatives, integrals, limits, optimization
- Geometry: areas, volumes, angles, proofs
- Statistics: probability, distributions, hypothesis testing
- Number Theory: primes, divisibility, modular arithmetic
- Linear Algebra: matrices, vectors, transformations
"""
    
    def __init__(self):
        super().__init__(name="parser")
        self.llm = get_llm_client()
    
    def execute(self, input_data: ParserInput) -> ParserOutput:
        """
        Parse raw problem text into structured format.
        
        Args:
            input_data: ParserInput with raw text
            
        Returns:
            ParserOutput with structured problem data
        """
        try:
            prompt = self._build_prompt(input_data.raw_text)
            
            # Get structured output from LLM with fallback
            fallback = {
                "problem_text": input_data.raw_text,
                "topic": "general",
                "variables": [],
                "constraints": [],
                "needs_clarification": False,
                "ambiguities": []
            }
            
            response = self.llm.generate_json(
                prompt=prompt,
                system_message=self.SYSTEM_PROMPT,
                fallback=fallback
            )
            
            # Validate and construct output
            ambiguities = response.get("ambiguities", [])
            needs_clarification = response.get("needs_clarification", False)
            
            # Trigger HITL if ambiguities exceed threshold
            requires_hitl = (
                len(ambiguities) >= settings.PARSER_AMBIGUITY_THRESHOLD or
                needs_clarification
            )
            
            if requires_hitl:
                self.logger.warning(
                    f"Parser HITL triggered: {len(ambiguities)} ambiguities found"
                )
            
            output = ParserOutput(
                problem_text=response.get("problem_text", input_data.raw_text),
                topic=response.get("topic", "general"),
                variables=response.get("variables", []),
                constraints=response.get("constraints", []),
                needs_clarification=needs_clarification,
                ambiguities=ambiguities,
                requires_human_review=requires_hitl,
                metadata={"raw_input_length": len(input_data.raw_text)}
            )
            
            self.logger.info(f"Parsed problem - Topic: {output.topic}, Variables: {len(output.variables)}, HITL: {requires_hitl}")
            return output
            
        except Exception as e:
            self.logger.error(f"Parsing failed: {str(e)}")
            raise ParsingError(f"Failed to parse problem: {str(e)}")
    
    def _build_prompt(self, raw_text: str) -> str:
        """Build the parsing prompt."""
        return f"""Analyze this problem and extract structured information:

PROBLEM:
{raw_text}

Return JSON with this exact structure:
{{
    "problem_text": "cleaned problem statement",
    "topic": "mathematical domain (e.g., algebra, calculus, geometry, statistics)",
    "variables": ["list", "of", "variables"],
    "constraints": ["list", "of", "constraints"],
    "needs_clarification": false,
    "ambiguities": ["any", "unclear", "aspects"]
}}
"""
