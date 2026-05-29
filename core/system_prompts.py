"""
core/system_prompts.py — System Prompts
=======================================
Centralized system prompts for the AI assistant.
Modular, maintainable, and dynamically configurable.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import hashlib


@dataclass
class SystemPrompt:
    """A system prompt component."""
    role: str = "system"
    content: str = ""
    priority: int = 0
    category: str = "general"
    dynamic: bool = False
    variables: List[str] = field(default_factory=list)
    hash: str = ""


@dataclass
class PromptTemplate:
    """Template for dynamic prompt generation."""
    name: str
    base_prompts: List[SystemPrompt]
    context_rules: Dict[str, Any]
    tone_rules: Dict[str, str]


class SystemPrompts:
    """
    Centralized system prompts with dynamic capabilities.
    
    Provides:
    - Base system prompts for different task types
    - Dynamic prompt generation based on context
    - Tone adaptation
    - Modular prompt components
    """
    
    BASE_PROMPT = """You are MIN AI, a sophisticated AI assistant with multimodal capabilities.

Your core characteristics:
- You think step by step before responding
- You verify assumptions before stating facts
- You adapt your communication style to the user
- You use tools when appropriate, not by default
- You maintain context across the conversation

Communication guidelines:
- Be concise but complete
- Use contextually appropriate greetings
- Provide specific answers, not generic ones
- When uncertain, acknowledge limitations
- Ask clarifying questions when needed"""

    REASONING_PROMPT = """When solving problems:
1. Break down complex tasks into steps
2. Consider multiple approaches
3. Verify intermediate results
4. Explain your reasoning when helpful
5. Correct mistakes when identified"""

    MEMORY_INTEGRATION_PROMPT = """Memory context:
- Use provided memory facts when relevant
- Do not repeat facts verbatim unless helpful
- Update your understanding based on new information
- Distinguish between historical facts and current instructions"""

    ACTION_PROMPT = """For action execution:
- Always validate parameters before execution
- Verify results after execution when possible
- Report success/failure clearly
- Suggest alternatives on failure
- Do not confirm actions that cannot be verified"""

    VISION_PROMPT = """When analyzing images:
- Describe what you observe objectively
- Connect visual elements to the user's query
- Note any relevant patterns or anomalies
- Use appropriate detail level for the task"""

    CODE_PROMPT = """For code-related tasks:
- Write clean, documented code
- Consider the user's skill level
- Explain non-obvious choices
- Provide working solutions
- Test edge cases"""

    TASK_TEMPLATES: Dict[str, str] = {
        "general": """You are a helpful AI assistant. Respond to the user's request helpfully and accurately.""",
        
        "reasoning": """You are an AI assistant focused on logical reasoning and problem-solving.
Think step by step. Show your work when helpful.""",
        
        "creative": """You are a creative AI assistant. Generate novel and appropriate ideas.
Balance creativity with practicality.""",
        
        "technical": """You are a technical AI assistant. Provide precise, accurate technical information.
When code is involved, ensure it is correct and well-documented.""",
        
        "analytical": """You are an analytical AI assistant. Analyze information objectively.
Present findings clearly with supporting evidence.""",
    }

    TONE_RULES: Dict[str, Dict[str, str]] = {
        "formal": {
            "greeting": "Good day. How may I assist you today?",
            "farewell": "Thank you for your consultation. Until next time.",
            "confirmation": "Understood. Proceeding as requested.",
            "error": "An error has occurred. Allow me to try an alternative approach.",
        },
        "casual": {
            "greeting": "Hey! What can I do for you?",
            "farewell": "Catch you later!",
            "confirmation": "Got it! On it.",
            "error": "Oops, something went wrong. Let me try that again.",
        },
        "technical": {
            "greeting": "System ready. Awaiting input.",
            "farewell": "Session terminated. Have a good day.",
            "confirmation": "Command acknowledged. Executing.",
            "error": "Exception detected. Implementing fallback strategy.",
        },
    }

    def __init__(self):
        self._current_tone = "casual"
        self._current_task_type = "general"
        self._context: Dict[str, Any] = {}

    def set_tone(self, tone: str) -> None:
        """Set communication tone."""
        if tone in self.TONE_RULES:
            self._current_tone = tone

    def set_task_type(self, task_type: str) -> None:
        """Set the current task type for specialized prompts."""
        self._current_task_type = task_type

    def update_context(self, context: Dict[str, Any]) -> None:
        """Update dynamic context variables."""
        self._context.update(context)

    def get_system_prompt(self, include_reasoning: bool = True) -> str:
        """Get the full system prompt for the current context."""
        parts = [self.BASE_PROMPT]
        
        if include_reasoning:
            parts.append(self.REASONING_PROMPT)
        
        parts.append(self.MEMORY_INTEGRATION_PROMPT)
        parts.append(self.ACTION_PROMPT)
        
        if self._context.get("has_vision"):
            parts.append(self.VISION_PROMPT)
        
        if self._current_task_type in self.TASK_TEMPLATES:
            parts.append(self.TASK_TEMPLATES[self._current_task_type])
        
        return "\n\n".join(parts)

    def get_greeting(self) -> str:
        """Get contextual greeting based on tone."""
        return self.TONE_RULES[self._current_tone]["greeting"]

    def get_farewell(self) -> str:
        """Get contextual farewell based on tone."""
        return self.TONE_RULES[self._current_tone]["farewell"]

    def get_confirmation(self) -> str:
        """Get contextual confirmation message."""
        return self.TONE_RULES[self._current_tone]["confirmation"]

    def get_error_message(self) -> str:
        """Get contextual error message."""
        return self.TONE_RULES[self._current_tone]["error"]

    def get_specialized_prompt(self, domain: str) -> Optional[str]:
        """Get specialized prompt for a specific domain."""
        prompts = {
            "code": self.CODE_PROMPT,
            "vision": self.VISION_PROMPT,
            "reasoning": self.REASONING_PROMPT,
            "action": self.ACTION_PROMPT,
        }
        return prompts.get(domain)

    def build_prompt_with_context(
        self,
        user_message: str,
        memory_context: Optional[List[Dict[str, Any]]] = None,
        has_vision: bool = False
    ) -> List[Dict[str, str]]:
        """Build a complete prompt with context.
        
        Returns a list of message dicts for chat completion.
        """
        messages = []
        
        system_prompt = self.get_system_prompt()
        if memory_context:
            memory_text = self._format_memory_context(memory_context)
            system_prompt += f"\n\n{memory_text}"
        if has_vision:
            system_prompt += f"\n\n{self.VISION_PROMPT}"
        
        messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})
        
        return messages

    def _format_memory_context(self, memory_entries: List[Dict[str, Any]]) -> str:
        """Format memory entries into a context string."""
        if not memory_entries:
            return ""
        
        lines = ["\nRelevant context from memory:"]
        for entry in memory_entries[:5]:
            content = entry.get("content", "")
            source = entry.get("source", "unknown")
            lines.append(f"- [{source}] {content}")
        
        return "\n".join(lines)

    def get_prompt_hash(self) -> str:
        """Get hash of current prompt configuration."""
        config = f"{self._current_tone}:{self._current_task_type}"
        return hashlib.md5(config.encode()).hexdigest()[:8]


def get_system_prompts() -> SystemPrompts:
    """Get the global SystemPrompts instance."""
    return SystemPrompts()
