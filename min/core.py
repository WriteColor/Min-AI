"""
min/core.py — MIN AI Core Processing Engine
==========================================
Main processing logic for the MIN AI assistant with
memory integration and tool execution.
"""

from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import asyncio

from memory import get_memory_service, MemoryService


class ProcessingMode(Enum):
    """MIN processing modes."""
    NORMAL = "normal"
    FAST = "fast"
    DEEP = "deep"
    CREATIVE = "creative"


@dataclass
class ToolResult:
    """Result from a tool execution."""
    success: bool
    tool_name: str
    output: Any
    error: Optional[str] = None
    duration_ms: float = 0


@dataclass
class MINResponse:
    """Response from MIN processing."""
    text: str
    mode: ProcessingMode
    tools_used: List[str] = field(default_factory=list)
    memory_updated: bool = False
    context_used: int = 0
    processing_time_ms: float = 0
    confidence: float = 1.0


class Tool:
    """Base class for MIN tools."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    async def execute(self, args: Dict[str, Any], memory: MemoryService) -> ToolResult:
        """Execute the tool with given arguments."""
        raise NotImplementedError
    
    def validate_args(self, args: Dict[str, Any]) -> bool:
        """Validate tool arguments."""
        return True


class MINCore:
    """
    Core processing engine for MIN AI assistant.
    Handles user input processing, memory management,
    tool orchestration, and response generation.
    """
    
    def __init__(self):
        self.memory = get_memory_service()
        self.tools: Dict[str, Tool] = {}
        self._processing_mode = ProcessingMode.NORMAL
        self._session_started = False
    
    def register_tool(self, tool: Tool) -> None:
        """Register a tool for use by MIN."""
        self.tools[tool.name] = tool
    
    def unregister_tool(self, name: str) -> None:
        """Unregister a tool."""
        if name in self.tools:
            del self.tools[name]
    
    async def process(
        self,
        user_input: str,
        context: Optional[str] = None,
        mode: ProcessingMode = ProcessingMode.NORMAL
    ) -> MINResponse:
        """
        Process user input and generate MIN response.
        
        Args:
            user_input: User's message or command
            context: Additional external context
            mode: Processing mode (normal, fast, deep, creative)
            
        Returns:
            MINResponse with generated text and metadata
        """
        start_time = datetime.now(timezone.utc)
        
        # Ensure session is active
        if not self._session_started:
            self.memory.start_session()
            self._session_started = True
        
        # Build full context
        full_context = self._build_context(user_input, context)
        
        # Log user input
        self.memory.log_user_message(user_input)
        
        # Generate response
        response_text = await self._generate_response(full_context, mode)
        
        # Log MIN response
        self.memory.log_min_response(response_text)
        
        # Calculate processing time
        duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        return MINResponse(
            text=response_text,
            mode=mode,
            tools_used=[],
            memory_updated=True,
            context_used=len(full_context),
            processing_time_ms=duration
        )
    
    async def _generate_response(
        self,
        context: str,
        mode: ProcessingMode
    ) -> str:
        """
        Generate response using context and mode.
        In production, this would call an LLM API.
        """
        # Placeholder for actual LLM integration
        # This would use OpenAI, Anthropic, or local model
        
        mode_prompt = {
            ProcessingMode.NORMAL: "Provide a balanced, helpful response.",
            ProcessingMode.FAST: "Respond concisely and directly.",
            ProcessingMode.DEEP: "Provide a thorough, detailed response.",
            ProcessingMode.CREATIVE: "Provide a creative, imaginative response."
        }
        
        # For now, return a placeholder response
        return f"[MIN {mode.value} mode] Processing: {context[:100]}..."
    
    def _build_context(self, user_input: str, external_context: Optional[str]) -> str:
        """Build full context for processing."""
        parts = []
        
        # Memory context
        memory_context = self.memory.build_system_context()
        if memory_context:
            parts.append(memory_context)
        
        # External context
        if external_context:
            parts.append(f"\n[EXTERNAL CONTEXT]\n{external_context}")
        
        # Current input
        parts.append(f"\n[CURRENT INPUT]\n{user_input}")
        
        return "\n".join(parts)
    
    async def execute_tool(
        self,
        tool_name: str,
        args: Dict[str, Any]
    ) -> ToolResult:
        """Execute a registered tool."""
        if tool_name not in self.tools:
            return ToolResult(
                success=False,
                tool_name=tool_name,
                output=None,
                error=f"Tool '{tool_name}' not found"
            )
        
        tool = self.tools[tool_name]
        start = datetime.now(timezone.utc)
        
        try:
            if not tool.validate_args(args):
                return ToolResult(
                    success=False,
                    tool_name=tool_name,
                    output=None,
                    error="Invalid tool arguments"
                )
            
            result = await tool.execute(args, self.memory)
            
            duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            result.duration_ms = duration
            
            # Log tool use
            self.memory.log_tool_use(tool_name, args, str(result.output))
            
            return result
        except Exception as e:
            duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            return ToolResult(
                success=False,
                tool_name=tool_name,
                output=None,
                error=str(e),
                duration_ms=duration
            )
    
    def set_mode(self, mode: ProcessingMode) -> None:
        """Set MIN processing mode."""
        self._processing_mode = mode
    
    @property
    def mode(self) -> ProcessingMode:
        return self._processing_mode
    
    async def end_session(self, outcome: str = "success") -> None:
        """End the current MIN session."""
        if self._session_started:
            self.memory.end_session(outcome)
            self._session_started = False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get MIN processing statistics."""
        return {
            "session_active": self._session_started,
            "mode": self._processing_mode.value,
            "registered_tools": list(self.tools.keys()),
            "memory_stats": self.memory.get_memory_stats()
        }


# Built-in tools

class CalculatorTool(Tool):
    """Simple calculator tool for math expressions."""
    
    def __init__(self):
        super().__init__("calculator", "Perform mathematical calculations")
    
    async def execute(self, args: Dict[str, Any], memory: MemoryService) -> ToolResult:
        expression = args.get("expression", "")
        try:
            result = eval(expression, {"__builtins__": {}}, {})
            return ToolResult(
                success=True,
                tool_name=self.name,
                output=str(result)
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                output=None,
                error=str(e)
            )
    
    def validate_args(self, args: Dict[str, Any]) -> bool:
        return "expression" in args


class ReminderTool(Tool):
    """Set reminders using work memory."""
    
    def __init__(self):
        super().__init__("reminder", "Set a reminder")
    
    async def execute(self, args: Dict[str, Any], memory: MemoryService) -> ToolResult:
        message = args.get("message", "")
        delay = args.get("delay_seconds", 60)
        
        from datetime import timedelta
        expires = (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat()
        
        import uuid
        reminder_id = f"reminder_{uuid.uuid4().hex[:8]}"
        
        memory.work_set(reminder_id, message, priority=5)
        
        return ToolResult(
            success=True,
            tool_name=self.name,
            output=f"Reminder set: {message}"
        )


def get_min_core() -> MINCore:
    """Get MIN core instance."""
    core = MINCore()
    core.register_tool(CalculatorTool())
    core.register_tool(ReminderTool())
    return core