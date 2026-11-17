from abc import ABC, abstractmethod
from typing import Any, Dict, Type
from pydantic import BaseModel


class ToolResult(BaseModel):
    """Normalized result returned by any executed tool."""
    success: bool
    tool_name: str
    data: Dict[str, Any]
    error_message: str | None = None


class BaseTool(ABC):
    """
    Abstract base class for all backend tools.
    Every tool must define its parameter validation schema and whether it requires human approval.
    """
    name: str
    description: str
    parameters_schema: Type[BaseModel]
    is_sensitive: bool = False  # If True, execution halts until human approval is granted

    @abstractmethod
    async def execute(self, params: BaseModel, context: Dict[str, Any]) -> ToolResult:
        """Executes the sandboxed backend action."""
        pass
