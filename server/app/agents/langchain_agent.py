"""
LangChain ReAct Agent - Uses LangChain's ReAct framework for enhanced reasoning.
Provides access to multiple tools and structured problem-solving.
"""

from typing import List, Dict, Any, Optional
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.tools import Tool
from langchain_core.prompts import PromptTemplate
from langchain.agents.output_parsers import ReActSingleInputOutputParser
from langchain.agents.format_scratchpad import format_log_to_str
from app.agents.base import BaseAgent
from app.agents.models import SolverInput, SolverOutput
from app.llm.client import get_llm_client
from app.agents.tools import CalculatorTool
from app.rag.retriever import get_rag_retriever
from app.core.exceptions import SolvingError
from sympy import sympify, simplify, solve as sympy_solve, latex
from sympy.parsing.sympy_parser import parse_expr
import re


class LangChainReActSolver(BaseAgent):
    """
    Advanced solver using LangChain's ReAct (Reasoning + Acting) framework.
    Provides access to multiple tools for mathematical problem solving.
    """
    
    def __init__(self):
        super().__init__(name="langchain_react_solver")
        self.llm_client = get_llm_client()
        self.calculator = CalculatorTool()
        self.rag = get_rag_retriever()
        
        # Initialize tools
        self.tools = self._create_tools()
        
        # Create ReAct agent
        self.agent_executor = self._create_agent_executor()
    
    def _create_tools(self) -> List[Tool]:
        """Create tools for the agent to use."""
        
        def calculator_tool(expression: str) -> str:
            """Calculate numerical expressions. Input should be a valid Python expression."""
            try:
                result = self.calculator.evaluate(expression)
                return f"Result: {result}"
            except Exception as e:
                return f"Error calculating: {str(e)}"
        
        def symbolic_solver_tool(equation: str) -> str:
            """
            Solve algebraic equations symbolically using SymPy.
            Input format: "x**2 + 2*x - 3 = 0" or "x**2 + 2*x - 3" (assumes = 0).
            Returns solutions for the variable.
            """
            try:
                # Parse equation
                if '=' in equation:
                    left, right = equation.split('=')
                    expr = parse_expr(left) - parse_expr(right)
                else:
                    expr = parse_expr(equation)
                
                # Solve for all symbols
                symbols = list(expr.free_symbols)
                if not symbols:
                    return f"No variables found in equation"
                
                solutions = sympy_solve(expr, symbols[0])
                
                # Format solutions
                if not solutions:
                    return "No solutions found"
                elif len(solutions) == 1:
                    return f"Solution: {symbols[0]} = {solutions[0]}"
                else:
                    sol_str = ', '.join([f"{symbols[0]} = {sol}" for sol in solutions])
                    return f"Solutions: {sol_str}"
                    
            except Exception as e:
                return f"Error solving equation: {str(e)}"
        
        def simplify_tool(expression: str) -> str:
            """
            Simplify mathematical expressions algebraically.
            Input: Any mathematical expression with variables.
            Returns: Simplified form.
            """
            try:
                expr = parse_expr(expression)
                simplified = simplify(expr)
                return f"Simplified: {simplified}"
            except Exception as e:
                return f"Error simplifying: {str(e)}"
        
        def latex_converter_tool(expression: str) -> str:
            """
            Convert mathematical expression to LaTeX format.
            Input: Mathematical expression.
            Returns: LaTeX representation.
            """
            try:
                expr = parse_expr(expression)
                latex_str = latex(expr)
                return f"LaTeX: ${latex_str}$"
            except Exception as e:
                return f"Error converting to LaTeX: {str(e)}"
        
        def rag_search_tool(query: str) -> str:
            """
            Search mathematical knowledge base for relevant examples and concepts.
            Input: Query describing what to search for.
            Returns: Relevant context from knowledge base.
            """
            try:
                results = self.rag.retrieve(query, k=3)
                if not results:
                    return "No relevant results found in knowledge base"
                
                output = "Relevant knowledge:\n"
                for i, result in enumerate(results, 1):
                    output += f"{i}. {result}\n"
                return output
            except Exception as e:
                return f"Error searching knowledge base: {str(e)}"
        
        # Create LangChain Tool objects
        return [
            Tool(
                name="calculator",
                func=calculator_tool,
                description="Useful for calculating numerical expressions. Input: valid Python math expression like '2+2' or 'sqrt(16)'. Use for arithmetic, trigonometry, logarithms, etc."
            ),
            Tool(
                name="symbolic_solver",
                func=symbolic_solver_tool,
                description="Solves algebraic equations symbolically. Input: equation like 'x**2 + 2*x - 3 = 0' or expression to solve for 0. Use for finding exact solutions to equations."
            ),
            Tool(
                name="simplify",
                func=simplify_tool,
                description="Simplifies mathematical expressions algebraically. Input: any expression with variables like '(x**2 - 4)/(x - 2)'. Returns simplified form."
            ),
            Tool(
                name="latex_converter",
                func=latex_converter_tool,
                description="Converts mathematical expressions to LaTeX format for display. Input: any mathematical expression. Useful for formatting final answers."
            ),
            Tool(
                name="knowledge_search",
                func=rag_search_tool,
                description="Searches the mathematical knowledge base for relevant examples, formulas, and concepts. Input: natural language query describing what you need. Use when you need background knowledge or similar examples."
            )
        ]
    
    def _create_agent_executor(self) -> AgentExecutor:
        """Create the ReAct agent executor."""
        
        # ReAct prompt template
        template = """You are an expert mathematical problem solver with access to powerful tools.

Use the following format for your reasoning:

Question: the input question you must solve
Thought: think step-by-step about what you need to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Available tools:
{tools}

Question: {input}
Thought: {agent_scratchpad}"""

        prompt = PromptTemplate.from_template(template)
        
        # Create agent
        from langchain.agents import AgentExecutor, create_react_agent
        
        agent = create_react_agent(
            llm=self.llm_client.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        # Create executor with optimized settings
        # verbose=False in production to reduce output
        from app.settings import settings
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=(settings.LOG_LEVEL == "DEBUG"),  # Only verbose in debug mode
            max_iterations=8,  # Reduced from 10 for faster timeout
            max_execution_time=45,  # Reduced from 60 for faster response
            handle_parsing_errors=True,
            return_intermediate_steps=True,
            early_stopping_method="generate"  # Generate final answer if max iterations reached
        )
        
        return agent_executor
    
    def execute(self, input_data: SolverInput) -> SolverOutput:
        """
        Solve the problem using LangChain ReAct agent.
        
        Args:
            input_data: SolverInput with problem and routing info
            
        Returns:
            SolverOutput with solution
        """
        try:
            parsed = input_data.parsed_problem
            routing = input_data.routing_info
            
            # Build comprehensive problem description
            problem_desc = f"""Solve this mathematical problem:

Problem: {parsed.problem_text}
Topic: {parsed.topic}
Type: {routing.problem_type}
Difficulty: {routing.difficulty_level}"""
            
            if parsed.variables:
                problem_desc += f"\nVariables: {', '.join(parsed.variables)}"
            if parsed.constraints:
                problem_desc += f"\nConstraints: {', '.join(parsed.constraints)}"
            
            problem_desc += "\n\nProvide a detailed solution with clear reasoning. Use tools as needed for calculations and verification."
            
            # Execute agent
            self.logger.info(f"Running LangChain ReAct agent...")
            result = self.agent_executor.invoke({"input": problem_desc})
            
            # Extract answer and steps
            answer = result.get("output", "No answer generated")
            intermediate_steps = result.get("intermediate_steps", [])
            
            # Format steps
            solution_steps = []
            tools_used = []
            reasoning = ""
            
            for step in intermediate_steps:
                if len(step) >= 2:
                    action, observation = step[0], step[1]
                    tool_name = action.tool if hasattr(action, 'tool') else str(action)
                    tool_input = action.tool_input if hasattr(action, 'tool_input') else ""
                    
                    if tool_name not in tools_used:
                        tools_used.append(tool_name)
                    
                    step_desc = f"Used {tool_name}: {tool_input} → {observation}"
                    solution_steps.append(step_desc)
                    reasoning += f"{step_desc}\n"
            
            # If no steps, create basic step
            if not solution_steps:
                solution_steps = ["Analyzed problem and generated solution"]
            
            output = SolverOutput(
                answer=answer,
                solution_steps=solution_steps,
                used_context=False,
                tools_used=tools_used,
                reasoning=reasoning or "Used ReAct framework for structured problem solving",
                metadata={
                    "problem_type": routing.problem_type,
                    "agent_type": "langchain_react",
                    "iterations": len(intermediate_steps)
                }
            )
            
            self.logger.info(
                f"LangChain ReAct solved problem - Tools: {tools_used}, "
                f"Iterations: {len(intermediate_steps)}"
            )
            return output
            
        except Exception as e:
            self.logger.error(f"LangChain ReAct solving failed: {str(e)}")
            raise SolvingError(f"Failed to solve with ReAct agent: {str(e)}")
