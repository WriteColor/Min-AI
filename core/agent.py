"""
core/agent.py — MIN AI Agent Orchestrator
==========================================
Main agent that orchestrates all subsystems: memory, providers,
actions, and context building.

Author: MIN AI Team
Version: 1.0
"""

import asyncio
import traceback
from typing import Optional, Dict, Any, List
from datetime import datetime

from memory.hybrid import HybridMemory
from memory.work_memory import WorkMemory
from providers.registry import get_registry, ProviderRegistry
from core.prompt_builder import PromptBuilder
from core.response_generator import ResponseGenerator


class IntentParser:
    """Parse user intent from text input."""
    
    def __init__(self):
        self._patterns = {
            'open_app': r'(?:abrir|abrir|launch|iniciar|start)\s+(.+)',
            'close_app': r'(?:cerrar|close|terminar)\s+(.+)',
            'search_web': r'(?:buscar|search|google|consultar)\s+(.+)',
            'write_file': r'(?:escribir|crear|make|create).*?(?:archivo|file)\s+(.+)',
            'read_file': r'(?:leer|read|abrir).*?(?:archivo|file)\s+(.+)',
            'system_info': r'(?:info|sistema|system|estad[ao])\s+(?:del|de)?\s*(?:pc|sistema)?',
            'calendar': r'(?:calendario|agenda|reunión|meeting)\s*(.*)',
            'weather': r'(?:clima|tiempo|weather)\s*(?:en|in)?\s*(\w+)?',
        }
    
    def parse(self, text: str) -> Dict[str, Any]:
        """Parse intent from user input."""
        text = text.lower().strip()
        
        for intent, pattern in self._patterns.items():
            import re
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return {
                    'intent': intent,
                    'params': match.groups() if match.groups() else {},
                    'raw_text': text
                }
        
        return {
            'intent': 'general',
            'params': {},
            'raw_text': text
        }


class ActionExecutor:
    """Execute actions with validation and verification."""
    
    def __init__(self):
        self._action_registry: Dict[str, callable] = {}
    
    def register(self, name: str, action: callable):
        """Register an action handler."""
        self._action_registry[name] = action
    
    async def execute(self, action_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an action with given parameters."""
        if action_name not in self._action_registry:
            return {'success': False, 'error': f'Unknown action: {action_name}'}
        
        try:
            action = self._action_registry[action_name]
            if asyncio.iscoroutinefunction(action):
                result = await action(**params)
            else:
                result = action(**params)
            return {'success': True, 'result': result}
        except Exception as e:
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    def list_actions(self) -> List[str]:
        """List registered actions."""
        return list(self._action_registry.keys())


class StateManager:
    """Manage agent state and session context."""
    
    def __init__(self):
        self._state = {
            'session_id': None,
            'user_name': None,
            'current_task': None,
            'last_action': None,
            'last_result': None,
            'isListening': False,
            'isSpeaking': False,
            'isThinking': False,
            'provider_name': None,
            'model_name': None,
            'start_time': None
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)
    
    def set(self, key: str, value: Any):
        self._state[key] = value
    
    def update(self, **kwargs):
        self._state.update(kwargs)
    
    def get_state(self) -> Dict[str, Any]:
        return self._state.copy()


class MINAgent:
    """
    Main orchestrator agent for MIN AI.
    Coordinates memory, providers, actions, and context.
    """
    
    def __init__(self):
        self.memory = HybridMemory()
        self.work_memory = WorkMemory()
        self.provider_registry = get_registry()
        self.prompt_builder = PromptBuilder(self.memory)
        self.response_generator = ResponseGenerator()
        self.intent_parser = IntentParser()
        self.action_executor = ActionExecutor()
        self.state_manager = StateManager()
        self._active_provider = None
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize all subsystems."""
        try:
            # Initialize memory
            await self.memory.initialize()
            
            # Load user profile from memory
            profile = await self.memory.get_semantic_facts(category='identity')
            if profile:
                name = profile.get('name')
                if name:
                    self.state_manager.set('user_name', name)
            
            self._initialized = True
            return True
        except Exception as e:
            print(f"[Agent] Initialization error: {e}")
            traceback.print_exc()
            return False
    
    async def process(self, user_input: str) -> str:
        """
        Process user input and generate response.
        
        Args:
            user_input: User's text input
            
        Returns:
            Agent's text response
        """
        if not self._initialized:
            await self.initialize()
        
        # Parse intent
        intent_data = self.intent_parser.parse(user_input)
        
        # Build context from memory
        context = await self.prompt_builder.build_context(user_input)
        
        # Store interaction in episodic memory
        await self.memory.add_interaction(
            user_input=user_input,
            agent_response="",  # Will be updated
            context=intent_data['intent']
        )
        
        # Update work memory with current task
        self.work_memory.set('current_input', user_input)
        self.work_memory.set('current_intent', intent_data['intent'])
        self.work_memory.set('timestamp', datetime.now().isoformat())
        
        # Execute action if applicable
        action_result = None
        if intent_data['intent'] != 'general':
            action_result = await self.action_executor.execute(
                intent_data['intent'],
                intent_data['params']
            )
            if action_result and action_result.get('success'):
                self.state_manager.set('last_action', intent_data['intent'])
                self.state_manager.set('last_result', action_result.get('result'))
        
        # Generate response
        self.state_manager.set('isThinking', True)
        
        try:
            # Build prompt with context
            prompt = self.prompt_builder.build_prompt(
                user_input=user_input,
                context=context,
                intent=intent_data,
                action_result=action_result
            )
            
            # Get response from provider
            if self._active_provider:
                response = await self._active_provider.chat(prompt)
            else:
                response = await self._generate_fallback_response(user_input, context)
            
            # Update interaction with response
            await self.memory.update_last_interaction(agent_response=response)
            
            # Generate contextual response
            contextual_response = self.response_generator.generate(
                response_text=response,
                intent=intent_data['intent'],
                user_name=self.state_manager.get('user_name')
            )
            
            self.state_manager.set('isThinking', False)
            
            return contextual_response
            
        except Exception as e:
            self.state_manager.set('isThinking', False)
            traceback.print_exc()
            return f"Error processing request: {str(e)}"
    
    async def _generate_fallback_response(self, user_input: str, context: Dict) -> str:
        """Generate response when no provider is active."""
        return f"I'm ready to help you with: {user_input[:50]}..."
    
    def set_provider(self, provider_name: str) -> bool:
        """Set active AI provider."""
        provider = self.provider_registry.get_provider(provider_name)
        if provider:
            self._active_provider = provider
            self.state_manager.set('provider_name', provider_name)
            return True
        return False
    
    def get_state(self) -> Dict[str, Any]:
        """Get current agent state."""
        return self.state_manager.get_state()
    
    async def shutdown(self):
        """Gracefully shutdown agent."""
        await self.memory.save_all()
        await self.provider_registry.shutdown_all()


# Global agent instance
_agent_instance = None


def get_agent() -> MINAgent:
    """Get global agent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = MINAgent()
    return _agent_instance