"""
Verifier/Critic Agent - Validates solution correctness and quality.
Checks units, domain validity, and edge cases. Triggers HITL when needed.
"""

from app.agents.base import BaseAgent
from app.agents.models import VerifierInput, VerifierOutput
from app.llm.client import get_llm_client
from app.settings import settings
from app.core.exceptions import VerificationError


class VerifierAgent(BaseAgent):
    """
    Verifies solution correctness and triggers human review when uncertain.
    Checks mathematical validity, units, domain constraints, and edge cases.
    Uses systematic verification approach.
    """
    
    SYSTEM_PROMPT = """You are a meticulous mathematical quality assurance expert. Your job is to ensure solutions are correct, complete, and reliable.

## 2-STEP VERIFICATION PROCESS:

### STEP 1: LOGICAL VERIFICATION
Before checking calculations, verify:
- Is the approach/method appropriate for this problem type?
- Does the solution address what was actually asked?
- Is the reasoning chain logically sound?
- Are there any logical gaps or unjustified steps?

### STEP 2: COMPUTATIONAL VERIFICATION
Check each calculation:
- Verify arithmetic operations are correct
- Check algebraic manipulations
- Validate units and dimensions
- Test with edge cases (0, negatives, large numbers)
- Substitute answer back to verify it satisfies original equation

## VERIFICATION CHECKLIST:
1. ✓ Method Selection: Is the solving approach correct?
2. ✓ Logical Flow: Does each step follow from the previous?
3. ✓ Calculations: Are all arithmetic/algebraic operations correct?
4. ✓ Units: Are units consistent and properly handled?
5. ✓ Domain: Does the answer satisfy domain constraints?
6. ✓ Reasonableness: Does the answer make intuitive sense?
7. ✓ Completeness: Are all parts of the question answered?
8. ✓ Edge Cases: Has the solution handled special cases?

## COMMON ERRORS TO WATCH FOR:
- Sign errors (positive/negative)
- Off-by-one errors
- Missing cases in piecewise solutions
- Division by zero risks
- Square root of negatives
- Logarithm of non-positive numbers
- Forgetting to check if solutions are extraneous
- Unit conversion errors

## CONFIDENCE GUIDELINES:
- 90-100%: Solution is definitely correct, verified multiple ways
- 75-89%: Solution appears correct, minor uncertainties
- 50-74%: Some concerns, recommend human review
- Below 50%: Significant issues detected, requires correction
"""
    
    def __init__(self):
        super().__init__(name="verifier")
        self.llm = get_llm_client()
    
    def execute(self, input_data: VerifierInput) -> VerifierOutput:
        """
        Verify the solution quality and correctness.
        
        Args:
            input_data: VerifierInput with problem and solution
            
        Returns:
            VerifierOutput with verification results
        """
        try:
            prompt = self._build_prompt(input_data)
            
            # Get verification from LLM with fallback
            fallback = {
                "is_correct": True,
                "confidence": 0.5,
                "correctness_issues": ["Unable to fully verify due to parsing error"],
                "unit_check_passed": True,
                "domain_check_passed": True,
                "edge_cases_checked": [],
                "requires_human_review": True
            }
            
            response = self.llm.generate_json(
                prompt=prompt,
                system_message=self.SYSTEM_PROMPT,
                fallback=fallback
            )
            
            # Determine if human review is needed
            confidence = response.get("confidence", 0.5)
            has_issues = len(response.get("correctness_issues", [])) > 0
            requires_human = (
                confidence < settings.VERIFIER_CONFIDENCE_THRESHOLD or
                has_issues or
                response.get("requires_human_review", False)
            )
            
            output = VerifierOutput(
                is_correct=response.get("is_correct", False),
                confidence=confidence,
                correctness_issues=response.get("correctness_issues", []),
                unit_check_passed=response.get("unit_check_passed", True),
                domain_check_passed=response.get("domain_check_passed", True),
                edge_cases_checked=response.get("edge_cases_checked", []),
                requires_human_review=requires_human,
                metadata={
                    "problem_topic": input_data.original_problem.topic,
                    "solution_steps_count": len(input_data.solution.solution_steps)
                }
            )
            
            self.logger.info(
                f"Verification complete - Correct: {output.is_correct}, "
                f"Confidence: {output.confidence:.2f}, "
                f"HITL Required: {output.requires_human_review}"
            )
            return output
            
        except Exception as e:
            self.logger.error(f"Verification failed: {str(e)}")
            raise VerificationError(f"Failed to verify solution: {str(e)}")
    
    def _build_prompt(self, input_data: VerifierInput) -> str:
        """Build the verification prompt."""
        problem = input_data.original_problem
        solution = input_data.solution
        
        return f"""Verify this mathematical solution thoroughly:

ORIGINAL PROBLEM: {problem.problem_text}
TOPIC: {problem.topic}
VARIABLES: {', '.join(problem.variables) if problem.variables else 'None'}
CONSTRAINTS: {', '.join(problem.constraints) if problem.constraints else 'None'}

PROPOSED SOLUTION:
Answer: {solution.answer}
Reasoning: {solution.reasoning}
Steps: {chr(10).join(f"{i+1}. {step if isinstance(step, str) else str(step)}" for i, step in enumerate(solution.solution_steps))}

VERIFICATION CHECKLIST:
1. Is the mathematical reasoning sound?
2. Are all units consistent and correct?
3. Does the answer satisfy domain constraints?
4. Are edge cases handled properly?
5. Are there any calculation errors?
6. Is the answer reasonable and makes sense?

Return JSON with this structure:
{{
    "is_correct": true/false,
    "confidence": 0.0-1.0,
    "correctness_issues": ["list any problems found"],
    "unit_check_passed": true/false,
    "domain_check_passed": true/false,
    "edge_cases_checked": ["edge case 1", "edge case 2"],
    "requires_human_review": true/false
}}

Set requires_human_review to true if:
- Confidence < 0.7
- Complex problem with ambiguity
- Potential errors detected
- Edge cases not fully covered
"""
