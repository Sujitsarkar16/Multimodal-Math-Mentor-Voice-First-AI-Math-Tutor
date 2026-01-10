"""
Base agent class providing common functionality for all agents.
Implements the Strategy pattern for agent behavior.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel
from app.core.logger import setup_logger


class AgentInput(BaseModel):
    """Base class for agent inputs."""
    pass


class AgentOutput(BaseModel):
    """Base class for agent outputs."""
    metadata: Dict[str, Any] = {}


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the system.
    Enforces a consistent interface and provides common functionality.
    """
    
    def __init__(self, name: str):
        """
        Initialize the base agent.
        
        Args:
            name: Unique identifier for this agent
        """
        self.name = name
        self.logger = setup_logger(f"agent.{name}")
        self._execution_count = 0
    
    @abstractmethod
    def execute(self, input_data: AgentInput) -> AgentOutput:
        """
        Execute the agent's primary function.
        
        Args:
            input_data: Validated input data
            
        Returns:
            AgentOutput containing results and metadata
        """
        pass
    
    def run(self, input_data: AgentInput) -> AgentOutput:
        """
        Run the agent with error handling and logging.
        
        Args:
            input_data: Validated input data
            
        Returns:
            AgentOutput with results
        """
        self._execution_count += 1
        self.logger.info(f"Executing {self.name} (run #{self._execution_count})")
        
        try:
            result = self.execute(input_data)
            self.logger.info(f"{self.name} completed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"{self.name} failed: {str(e)}", exc_info=True)
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent execution statistics."""
        return {
            "name": self.name,
            "execution_count": self._execution_count
        }
