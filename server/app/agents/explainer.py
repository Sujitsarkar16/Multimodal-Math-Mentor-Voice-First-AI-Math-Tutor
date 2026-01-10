"""
Explainer/Tutor Agent - Creates student-friendly step-by-step explanations.
Produces educational content with key concepts and common mistakes.
"""

from app.agents.base import BaseAgent
from app.agents.models import ExplainerInput, ExplainerOutput
from app.llm.client import get_llm_client
from app.core.exceptions import AgentError


class ExplainerAgent(BaseAgent):
    """
    Generates pedagogical explanations of solutions.
    Focuses on student understanding with clear steps and concept explanations.
    Uses 2-step Chain of Thought for comprehensive teaching.
    """
    
    SYSTEM_PROMPT = """You are an exceptional mathematics teacher known for making complex concepts simple and accessible. Your explanations should feel like a patient one-on-one tutoring session.

## 2-STEP CHAIN OF THOUGHT TEACHING METHOD:

### STEP 1: CONCEPTUAL FOUNDATION
Before explaining the solution:
- What fundamental concept(s) does this problem test?
- What prerequisite knowledge does the student need?
- What's the "big picture" understanding the student should gain?
- How does this connect to things they already know?

### STEP 2: GUIDED WALKTHROUGH
For each step of the solution:
- State what we're doing in simple terms
- Explain WHY this step is necessary (the reasoning)
- Show the mathematics clearly with LaTeX
- Translate the result into plain language
- Anticipate: "What might confuse a student here?"

## TEACHING PRINCIPLES:
1. **Start with the "Why"**: Begin by explaining why we approach it this way
2. **Visual Language**: Use analogies and visual descriptions when possible
3. **Build Connections**: Link new concepts to familiar ones
4. **Highlight Pitfalls**: Warn about common mistakes BEFORE they happen
5. **Celebrate Progress**: Acknowledge complexity while remaining encouraging
6. **Verify Understanding**: End with a summary that reinforces key takeaways

## TONE & STYLE:
- Warm, patient, and encouraging
- "Let's work through this together..."
- "The key insight here is..."
- "Students often make the mistake of... Instead, remember to..."
- "Think of it this way..."

## FORMAT EACH STEP AS:
📌 **Step N: [What we're doing]**
*Why this step?* [Brief explanation of the reasoning]
*The Math:* $[LaTeX expression]$
*In words:* [Plain language interpretation]
⚠️ *Watch out for:* [Common mistake if applicable]
"""
    
    def __init__(self):
        super().__init__(name="explainer")
        self.llm = get_llm_client()
    
    def execute(self, input_data: ExplainerInput) -> ExplainerOutput:
        """
        Generate educational explanation of the solution.
        
        Args:
            input_data: ExplainerInput with problem, solution, and verification
            
        Returns:
            ExplainerOutput with student-friendly explanation
        """
        try:
            prompt = self._build_prompt(input_data)
            
            # Generate explanation with fallback
            fallback = {
                "explanation": input_data.solution.reasoning or "The solution was computed successfully.",
                "step_by_step": input_data.solution.solution_steps,
                "key_concepts": [],
                "common_mistakes": [],
                "difficulty_rating": 3
            }
            
            response = self.llm.generate_json(
                prompt=prompt,
                system_message=self.SYSTEM_PROMPT,
                fallback=fallback
            )
            
            output = ExplainerOutput(
                explanation=response.get("explanation", "No explanation generated"),
                step_by_step=response.get("step_by_step", []),
                key_concepts=response.get("key_concepts", []),
                common_mistakes=response.get("common_mistakes", []),
                difficulty_rating=response.get("difficulty_rating", 3),
                metadata={
                    "problem_topic": input_data.original_problem.topic,
                    "verification_confidence": input_data.verification.confidence
                }
            )
            
            self.logger.info(
                f"Generated explanation - Difficulty: {output.difficulty_rating}/5, "
                f"Concepts: {len(output.key_concepts)}, "
                f"Steps: {len(output.step_by_step)}"
            )
            return output
            
        except Exception as e:
            self.logger.error(f"Explanation generation failed: {str(e)}")
            raise AgentError(f"Failed to generate explanation: {str(e)}")
    
    def _build_prompt(self, input_data: ExplainerInput) -> str:
        """Build the explanation prompt with 2-step Chain of Thought."""
        problem = input_data.original_problem
        solution = input_data.solution
        verification = input_data.verification
        
        verification_note = ""
        if not verification.is_correct or verification.correctness_issues:
            verification_note = f"""
⚠️ IMPORTANT: The solution has some issues that need to be addressed:
{chr(10).join(f"- {issue if isinstance(issue, str) else str(issue)}" for issue in verification.correctness_issues)}
Please incorporate corrections and explain why the original approach had issues.
"""
        
        return f"""## YOUR TASK
Create a comprehensive, teacher-quality explanation of this mathematical solution.
Imagine you are tutoring a student one-on-one who needs to deeply understand this problem.

## THE PROBLEM
**Question:** {problem.problem_text}
**Topic:** {problem.topic}

## THE SOLUTION TO EXPLAIN
**Final Answer:** {solution.answer}

**Solution Steps:**
{chr(10).join(f"{i+1}. {step if isinstance(step, str) else str(step)}" for i, step in enumerate(solution.solution_steps))}

**Reasoning Used:** {solution.reasoning}

{verification_note}

## VERIFICATION STATUS
- Correctness: {"✓ Verified" if verification.is_correct else "✗ Issues Found"}
- Confidence: {verification.confidence:.0%}
- Unit Check: {"✓ Passed" if verification.unit_check_passed else "✗ Failed"}
- Domain Check: {"✓ Passed" if verification.domain_check_passed else "✗ Failed"}

## REQUIRED OUTPUT (JSON)
Use the 2-step Chain of Thought method to create your explanation:

{{
    "explanation": "A comprehensive, warm, teacher-like explanation that:
        - STEP 1 (Conceptual Foundation): Starts by explaining what this problem is really testing and why the approach works
        - STEP 2 (Guided Walkthrough): Walks through each step explaining WHAT and WHY in simple terms
        - Uses analogies and real-world connections where helpful
        - Ends with a summary of key takeaways
        Format with proper paragraphs and use $LaTeX$ for math expressions.",
    
    "step_by_step": [
        "📌 **Step 1: [Title]** — *Why?* [Reasoning] — *Math:* $expression$ — *Result:* [Plain language]",
        "📌 **Step 2: [Title]** — *Why?* [Reasoning] — *Math:* $expression$ — *Result:* [Plain language]",
        "...continue for all steps...",
        "✅ **Final Answer:** [Clear statement] — *Verification:* [Quick sanity check]"
    ],
    
    "key_concepts": [
        "🔑 **[Concept Name]**: [Clear 1-2 sentence explanation of the concept and why it matters]",
        "🔑 **[Concept Name]**: [Explanation]"
    ],
    
    "common_mistakes": [
        "⚠️ **[Mistake Type]**: [What students often do wrong and how to avoid it]",
        "⚠️ **[Mistake Type]**: [Description and prevention tip]"
    ],
    
    "difficulty_rating": [1-5, where 1=very easy, 3=moderate, 5=very challenging]
}}

## QUALITY REQUIREMENTS:
1. The explanation should feel like a patient tutor, not a textbook
2. Every step must have both WHAT and WHY
3. Use encouraging language ("Great question!", "Let's work through this...")
4. Include at least 2-3 key concepts with clear explanations
5. Include at least 2 common mistakes students should avoid
6. Use LaTeX for ALL mathematical expressions
"""
