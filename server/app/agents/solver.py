"""
Solver Agent - Solves mathematical problems using RAG and tools.
Implements the core problem-solving logic with LangChain.
"""

from typing import List, Optional, Dict, Any, Tuple
from app.agents.base import BaseAgent
from app.agents.models import SolverInput, SolverOutput
from app.agents.tools import ToolRegistry, CalculatorTool
from app.llm.client import get_llm_client
from app.memory.recall import get_memory_recall
from app.core.exceptions import SolvingError


class SolverAgent(BaseAgent):
    """
    Solves mathematical problems using RAG, LLM, memory patterns, and computational tools.
    Combines retrieval-augmented generation with self-learning from past solutions.
    Uses 2-step Chain of Thought for thorough solutions.
    """
    
    SYSTEM_PROMPT = """You are an expert mathematics teacher and problem solver. You MUST solve problems like a patient, thorough teacher who shows EVERY step.

## 2-STEP CHAIN OF THOUGHT PROCESS:

### STEP 1: UNDERSTAND & PLAN (Think before solving)
Before solving, explicitly state:
- What is being asked? (Identify the goal)
- What information is given? (List all known values)
- What approach/formula will you use? (Strategy selection)
- Why is this approach appropriate? (Justify your method)

### STEP 2: EXECUTE & EXPLAIN (Solve step-by-step)
For EVERY calculation step:
- State what you're doing and WHY
- Show the mathematical operation clearly
- Explain the result in plain language
- Connect to the next step

## TEACHING GUIDELINES:
- Write as if teaching a student who needs to understand, not just get the answer
- NEVER skip steps - show intermediate calculations
- Use proper mathematical notation (LaTeX format)
- Explain the "why" behind each operation
- Highlight key concepts and formulas used
- Point out where students commonly make mistakes
- Verify your answer makes sense (sanity check)
- Learn from similar problems that were solved correctly before

## EXAMPLE FORMAT:
**Understanding the Problem:**
We need to find X given Y and Z...

**Planning the Solution:**
We'll use [formula/method] because [reason]...

**Step-by-Step Solution:**
Step 1: [Action] because [reason]
  $expression = result$
  This gives us [interpretation]...

Step 2: [Next action]...
[Continue until complete]

**Final Answer:** [Clear statement with units if applicable]
**Verification:** [Quick check that answer is reasonable]

Available tools:
- calculator: For numerical computations
- symbolic_solver: For algebraic manipulations
"""
    
    def __init__(self):
        super().__init__(name="solver")
        self.llm = get_llm_client()
        self.memory_recall = get_memory_recall()  # Self-learning memory system
        self.calculator = CalculatorTool()
    
    def execute(self, input_data: SolverInput) -> SolverOutput:
        """
        Solve the mathematical problem using RAG context and learned memory patterns.
        
        Args:
            input_data: SolverInput with problem and routing info
            
        Returns:
            SolverOutput with solution and steps
        """
        try:
            # Retrieve relevant context from both RAG and memory (self-learning)
            rag_contexts, memory_patterns = self._retrieve_context(input_data)
            
            # Build solving prompt with both sources of knowledge
            prompt = self._build_prompt(input_data, rag_contexts, memory_patterns)
            
            # Generate solution with fallback
            fallback = {
                "answer": "Unable to generate solution due to parsing error",
                "solution_steps": ["Please try rephrasing the problem"],
                "reasoning": "JSON parsing failed",
                "tool_calls": []
            }
            
            response = self.llm.generate_json(
                prompt=prompt,
                system_message=self.SYSTEM_PROMPT,
                fallback=fallback
            )
            
            # Process tool calls if any
            tools_used = self._process_tool_calls(response)
            
            # If tools were used, regenerate with results
            if tools_used:
                prompt = self._update_prompt_with_tools(prompt, tools_used)
                response = self.llm.generate_json(
                    prompt=prompt,
                    system_message=self.SYSTEM_PROMPT,
                    fallback=response  # Use previous response as fallback
                )
            
            output = SolverOutput(
                answer=response.get("answer", "No answer generated"),
                solution_steps=response.get("solution_steps", []),
                used_context=bool(rag_contexts or memory_patterns),
                tools_used=[t["tool"] for t in tools_used],
                reasoning=response.get("reasoning", ""),
                metadata={
                    "problem_type": input_data.routing_info.problem_type,
                    "rag_context_count": len(rag_contexts) if rag_contexts else 0,
                    "memory_patterns_count": len(memory_patterns) if memory_patterns else 0,
                    "self_learning_active": bool(memory_patterns)
                }
            )
            
            self.logger.info(
                f"Solved problem - Answer: {output.answer[:50]}..., "
                f"Steps: {len(output.solution_steps)}, "
                f"Tools: {output.tools_used}"
            )
            return output
            
        except Exception as e:
            self.logger.error(f"Solving failed: {str(e)}")
            raise SolvingError(f"Failed to solve problem: {str(e)}")
    
    def _retrieve_context(self, input_data: SolverInput) -> Tuple[Optional[List[str]], Optional[List[Dict[str, Any]]]]:
        """
        Retrieve relevant context using both RAG and memory patterns.
        This enables self-learning from previously solved problems.
        
        Returns:
            Tuple of (rag_contexts, memory_patterns)
        """
        if input_data.retrieved_context:
            return input_data.retrieved_context, None
        
        try:
            # Build query from problem
            query = f"{input_data.parsed_problem.topic}: {input_data.parsed_problem.problem_text}"
            topic = input_data.parsed_problem.topic
            
            # Use combined context retrieval (RAG + Memory patterns)
            rag_contexts, memory_patterns = self.memory_recall.get_combined_context(
                query=query,
                topic=topic
            )
            
            self.logger.info(
                f"Self-learning context: {len(rag_contexts)} RAG docs, "
                f"{len(memory_patterns)} learned patterns"
            )
            
            return rag_contexts if rag_contexts else None, memory_patterns if memory_patterns else None
            
        except Exception as e:
            self.logger.warning(f"Context retrieval failed: {str(e)}")
            return None, None
    
    def _process_tool_calls(self, response: dict) -> List[dict]:
        """Process any tool calls in the response."""
        tool_calls = response.get("tool_calls", [])
        results = []
        
        for call in tool_calls:
            tool_name = call.get("tool")
            args = call.get("args", {})
            
            try:
                if tool_name == "calculator":
                    expression = args.get("expression", "")
                    result = self.calculator.evaluate(expression)
                    results.append({
                        "tool": tool_name,
                        "input": expression,
                        "output": result
                    })
                    self.logger.info(f"Tool call: {tool_name}({expression}) = {result}")
                else:
                    tool = ToolRegistry.get_tool(tool_name)
                    if tool:
                        # Generic tool invocation
                        results.append({
                            "tool": tool_name,
                            "input": args,
                            "output": "Tool executed"
                        })
                        
            except Exception as e:
                self.logger.error(f"Tool call failed: {tool_name} - {str(e)}")
        
        return results
    
    def _build_prompt(
        self,
        input_data: SolverInput,
        rag_contexts: Optional[List[str]],
        memory_patterns: Optional[List[Dict[str, Any]]]
    ) -> str:
        """
        Build the solving prompt with 2-step Chain of Thought.
        Incorporates both RAG context and learned memory patterns for self-learning.
        """
        parsed = input_data.parsed_problem
        routing = input_data.routing_info
        
        prompt = f"""Solve this mathematical problem like an expert teacher showing every step:

## PROBLEM
{parsed.problem_text}

## PROBLEM CLASSIFICATION
- Type: {routing.problem_type}
- Difficulty: {routing.difficulty_level}
- Recommended Strategy: {routing.recommended_strategy}
"""
        
        if parsed.variables:
            prompt += f"\n## KNOWN VARIABLES\n{', '.join(parsed.variables)}"
        
        if parsed.constraints:
            prompt += f"\n## CONSTRAINTS\n{', '.join(parsed.constraints)}"
        
        # Add RAG context (knowledge base)
        if rag_contexts:
            prompt += f"\n\n## RELEVANT KNOWLEDGE BASE (Reference material):\n"
            for i, ctx in enumerate(rag_contexts, 1):
                prompt += f"{i}. {ctx}\n"
        
        # Add MEMORY PATTERNS (Self-learning from past solutions)
        if memory_patterns:
            prompt += f"\n\n## LEARNED PATTERNS FROM SIMILAR PROBLEMS (Use these as guidance):\n"
            prompt += "These are solutions that were verified as CORRECT by users. Learn from their approach:\n\n"
            for i, pattern in enumerate(memory_patterns, 1):
                if pattern.get("type") == "similar_problem":
                    prompt += f"### Similar Problem {i}:\n"
                    prompt += f"**Problem:** {pattern.get('problem', 'N/A')}\n"
                    prompt += f"**Verified Solution:** {pattern.get('solution', 'N/A')}\n"
                    prompt += f"**Confidence:** {pattern.get('confidence', 0):.0%}\n\n"
                else:
                    prompt += f"### Pattern {i}:\n"
                    prompt += f"**Problem Type:** {pattern.get('problem', 'N/A')}\n"
                    if pattern.get('solution_steps'):
                        steps = pattern.get('solution_steps', [])
                        steps_str = ' → '.join(s if isinstance(s, str) else str(s) for s in steps)
                        prompt += f"**Solution Approach:** {steps_str}\n"
                    prompt += f"**Answer Format:** {pattern.get('answer', 'N/A')}\n\n"
        
        prompt += """

## REQUIRED OUTPUT FORMAT (JSON)
Use the 2-step Chain of Thought process:

{
    "reasoning": "STEP 1 - UNDERSTAND & PLAN: [What is asked? What is given? What approach?] STEP 2 - EXECUTE: [Detailed step-by-step solution with explanations]",
    "solution_steps": [
        "Step 1: [Action] - [Explanation of why this step] → Result: [intermediate result]",
        "Step 2: [Next action] - [Explanation] → Result: [intermediate result]",
        "Step 3: ...",
        "Final: [Clear final answer with verification]"
    ],
    "answer": "Final answer with proper formatting and units if applicable",
    "tool_calls": [{"tool": "calculator", "args": {"expression": "2+2"}}]
}

## IMPORTANT INSTRUCTIONS:
1. Each solution_step MUST explain WHAT you're doing and WHY
2. Show ALL intermediate calculations - never skip steps
3. Use LaTeX notation for math expressions ($expression$)
4. Include a verification/sanity check in your reasoning
5. The answer should be clear and complete
6. If similar problems are provided, learn from their solution approach

If you need calculations, include them in tool_calls.
"""
        
        return prompt
    
    def _update_prompt_with_tools(self, original_prompt: str, tool_results: List[dict]) -> str:
        """Update prompt with tool execution results."""
        results_text = "\n\nTOOL RESULTS:\n"
        for result in tool_results:
            results_text += f"- {result['tool']}({result['input']}) = {result['output']}\n"
        
        return original_prompt + results_text + "\n\nNow complete the solution using these results."
