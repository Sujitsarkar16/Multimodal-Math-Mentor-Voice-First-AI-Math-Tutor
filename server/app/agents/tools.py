"""
Tool implementations for the Solver Agent.
Provides calculators, symbolic solvers, and other utilities.
"""

from typing import Any, Dict
import operator
from functools import reduce
from app.core.logger import setup_logger


logger = setup_logger(__name__)


class CalculatorTool:
    """Safe calculator for numerical computations."""
    
    # Allowed operations
    OPERATORS = {
        '+': operator.add,
        '-': operator.sub,
        '*': operator.mul,
        '/': operator.truediv,
        '**': operator.pow,
        '^': operator.pow,
    }
    
    @staticmethod
    def evaluate(expression: str) -> float:
        """
        Safely evaluate a mathematical expression.
        
        Args:
            expression: Math expression string
            
        Returns:
            Computed result
        """
        try:
            # Basic safety: only allow numbers and operators
            allowed_chars = set('0123456789+-*/^(). ')
            if not all(c in allowed_chars for c in expression):
                raise ValueError("Invalid characters in expression")
            
            # Replace ^ with **
            expression = expression.replace('^', '**')
            
            # Evaluate safely
            result = eval(expression, {"__builtins__": {}}, {})
            
            logger.info(f"Calculated: {expression} = {result}")
            return float(result)
            
        except Exception as e:
            logger.error(f"Calculation failed: {str(e)}")
            raise ValueError(f"Cannot evaluate expression: {str(e)}")


class SymbolicSolverTool:
    """Symbolic math solver (placeholder for SymPy integration)."""
    
    @staticmethod
    def solve_equation(equation: str, variable: str = "x") -> Dict[str, Any]:
        """
        Solve an equation symbolically.
        
        Args:
            equation: Equation to solve
            variable: Variable to solve for
            
        Returns:
            Solution dictionary
        """
        # Placeholder - in production, integrate SymPy
        logger.info(f"Symbolic solve requested: {equation} for {variable}")
        
        return {
            "solutions": ["Symbolic solver not fully implemented"],
            "method": "placeholder",
            "steps": []
        }


class PlotterTool:
    """Plotting tool (placeholder for matplotlib integration)."""
    
    @staticmethod
    def plot_function(function: str, x_range: tuple) -> Dict[str, Any]:
        """
        Plot a mathematical function.
        
        Args:
            function: Function to plot
            x_range: (min, max) range
            
        Returns:
            Plot information
        """
        logger.info(f"Plot requested: {function} over {x_range}")
        
        return {
            "plot_generated": False,
            "message": "Plotter not fully implemented",
            "function": function,
            "range": x_range
        }


class ToolRegistry:
    """Registry of available tools for the Solver Agent."""
    
    _tools = {
        "calculator": CalculatorTool(),
        "symbolic_solver": SymbolicSolverTool(),
        "plotter": PlotterTool(),
    }
    
    @classmethod
    def get_tool(cls, name: str):
        """Get a tool by name."""
        tool = cls._tools.get(name)
        if tool is None:
            logger.warning(f"Tool not found: {name}")
        return tool
    
    @classmethod
    def list_tools(cls):
        """List all available tools."""
        return list(cls._tools.keys())
