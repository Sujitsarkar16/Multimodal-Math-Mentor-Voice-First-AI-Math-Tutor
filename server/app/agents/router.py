"""
Intent Router Agent - Classifies problem type and determines solving strategy.
Routes workflow based on problem characteristics.
"""

from app.agents.base import BaseAgent
from app.agents.models import IntentRouterInput, IntentRouterOutput
from app.llm.client import get_llm_client
from app.core.exceptions import AgentError


class IntentRouterAgent(BaseAgent):
    """
    Classifies problem type and determines optimal solving strategy.
    Routes to appropriate tools and methods.
    Uses systematic classification approach.
    """
    
    SYSTEM_PROMPT = """You are an expert mathematical problem classifier and strategist. Your role is to accurately categorize problems and recommend the optimal solving approach.

## 2-STEP CLASSIFICATION PROCESS:

### STEP 1: PROBLEM IDENTIFICATION
Analyze the problem to determine:
- What mathematical domain does this belong to?
- What is the specific problem subtype?
- What is the primary operation required?
- What level of mathematical knowledge is needed?

### STEP 2: STRATEGY SELECTION
Based on identification, recommend:
- The best solving method/approach
- Required computational tools
- Expected difficulty level
- Key techniques to apply

## PROBLEM TYPE TAXONOMY:

### ALGEBRA
- linear_equation: Single variable linear equations
- quadratic_equation: ax² + bx + c = 0 forms
- polynomial_equation: Higher degree polynomials
- system_of_equations: Multiple equations, multiple unknowns
- inequality: Solving inequalities
- absolute_value: Equations/inequalities with |x|
- rational_equation: Equations with fractions
- radical_equation: Equations with roots

### CALCULUS
- derivative: Finding derivatives
- integral_definite: Definite integrals
- integral_indefinite: Antiderivatives
- limits: Limit calculations
- optimization: Max/min problems
- related_rates: Rate of change problems
- differential_equation: ODEs, PDEs
- series_convergence: Series and sequences

### GEOMETRY
- area_calculation: Finding areas
- volume_calculation: Finding volumes
- angle_calculation: Working with angles
- coordinate_geometry: Analytic geometry
- trigonometry: Trig functions and identities
- proof: Geometric proofs

### STATISTICS & PROBABILITY
- probability_basic: Simple probability
- probability_conditional: P(A|B) problems
- statistics_descriptive: Mean, median, mode, std
- statistics_inferential: Hypothesis testing
- combinatorics: Counting problems

## DIFFICULTY ASSESSMENT:
- **easy**: Single concept, straightforward application
- **medium**: Multiple concepts or multi-step solution
- **hard**: Complex reasoning, advanced techniques, or tricky edge cases

## TOOLS SELECTION:
- calculator: Numerical computations
- symbolic_solver: Algebraic manipulations, equation solving
- numerical_solver: Numerical methods, approximations
- plotter: Graphing, visualization
- matrix_solver: Linear algebra operations
"""
    
    # Problem type to tools mapping
    TOOL_RECOMMENDATIONS = {
        "arithmetic": ["calculator"],
        "algebra": ["symbolic_solver", "calculator"],
        "calculus": ["symbolic_solver", "calculator"],
        "geometry": ["plotter", "calculator"],
        "statistics": ["calculator", "plotter"],
        "probability": ["calculator"],
        "linear_algebra": ["matrix_solver", "calculator"],
        "differential_equations": ["symbolic_solver", "numerical_solver"]
    }
    
    def __init__(self):
        super().__init__(name="intent_router")
        self.llm = get_llm_client()
    
    def execute(self, input_data: IntentRouterInput) -> IntentRouterOutput:
        """
        Classify problem and determine routing strategy.
        
        Args:
            input_data: IntentRouterInput with parsed problem
            
        Returns:
            IntentRouterOutput with classification and routing info
        """
        try:
            parsed = input_data.parsed_problem
            prompt = self._build_prompt(parsed)
            
            # Get classification from LLM with fallback
            fallback = {
                "problem_type": "general",
                "difficulty_level": "medium",
                "recommended_strategy": "general_solving",
                "requires_tools": ["calculator"],
                "confidence": 0.5
            }
            
            response = self.llm.generate_json(
                prompt=prompt,
                system_message=self.SYSTEM_PROMPT,
                fallback=fallback
            )
            
            # Enhance with tool recommendations
            problem_type = response.get("problem_type", "general")
            tools = response.get("requires_tools", [])
            
            # Add recommended tools based on topic
            topic = parsed.topic.lower()
            for key, recommended_tools in self.TOOL_RECOMMENDATIONS.items():
                if key in topic or key in problem_type:
                    tools.extend([t for t in recommended_tools if t not in tools])
            
            output = IntentRouterOutput(
                problem_type=problem_type,
                difficulty_level=response.get("difficulty_level", "medium"),
                recommended_strategy=response.get("recommended_strategy", "general_solving"),
                requires_tools=tools,
                confidence=response.get("confidence", 0.8),
                metadata={
                    "topic": parsed.topic,
                    "has_constraints": len(parsed.constraints) > 0
                }
            )
            
            self.logger.info(
                f"Routed problem - Type: {output.problem_type}, "
                f"Difficulty: {output.difficulty_level}, "
                f"Tools: {output.requires_tools}"
            )
            return output
            
        except Exception as e:
            self.logger.error(f"Routing failed: {str(e)}")
            raise AgentError(f"Failed to route problem: {str(e)}")
    
    def _build_prompt(self, parsed_problem) -> str:
        """Build the routing prompt."""
        return f"""Classify this mathematical problem and recommend a solving strategy:

PROBLEM: {parsed_problem.problem_text}
TOPIC: {parsed_problem.topic}
VARIABLES: {', '.join(parsed_problem.variables) if parsed_problem.variables else 'None'}
CONSTRAINTS: {', '.join(parsed_problem.constraints) if parsed_problem.constraints else 'None'}

Return JSON with this exact structure:
{{
    "problem_type": "specific_type (e.g., quadratic_equation, derivative_calculation)",
    "difficulty_level": "easy|medium|hard",
    "recommended_strategy": "description of solving approach",
    "requires_tools": ["list", "of", "needed", "tools"],
    "confidence": 0.95
}}

Available tools: calculator, symbolic_solver, numerical_solver, plotter, matrix_solver
"""
