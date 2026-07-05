"""
Session Manager Module for ChitraGupta 2.0
Handles daily session segmentation and session boundaries.
"""

from datetime import datetime, date
from typing import Dict, Any, Optional
from .conversation_manager import ConversationManager, ConversationState
import sys


class SessionManager:
    def __init__(self, user_id: str = "default_user"):
        self.user_id = user_id
        self.conversation_manager = ConversationManager(user_id)
        self.session_start_date: Optional[date] = None
        self.session_data: Dict[str, Any] = {}
        
    def start_new_session(self) -> ConversationManager:
        """Start a new session, checking for day boundary."""
        today = date.today()
        
        # Check if we need to start a new day
        if self.session_start_date != today:
            # End previous session if exists
            if self.session_start_date is not None:
                self._end_session()
                
            # Start new session
            self.session_start_date = today
            self.conversation_manager.reset_for_new_day()
            
        return self.conversation_manager
    
    def _end_session(self):
        """End current session and prepare for daily summary."""
        # In a full implementation, this would trigger daily summary creation
        # For now, we just note that the session ended
        pass
        
    def get_conversation_manager(self) -> ConversationManager:
        """Get the current conversation manager."""
        return self.conversation_manager
        
    def update_conversation_state(self, user_input: str, context: Dict[str, Any]) -> ConversationState:
        """Update conversation state based on user input."""
        return self.conversation_manager.update_state(user_input, context)
        
    def should_create_task(self) -> bool:
        """Check if we should create a task based on current state."""
        return self.conversation_manager.should_create_task()
        
    def get_task_generation_context(self) -> Dict[str, Any]:
        """Get context for task generation."""
        return self.conversation_manager.get_context_for_task_generation()
        
    def get_session_info(self) -> Dict[str, Any]:
        """Get information about the current session."""
        return {
            "user_id": self.user_id,
            "session_start_date": self.session_start_date.isoformat() if self.session_start_date else None,
            "conversation_state": self.conversation_manager.state.value,
            "conversation_count": self.conversation_manager.context.conversation_count,
            "last_interaction": self.conversation_manager.context.last_interaction.isoformat() if self.conversation_manager.context.last_interaction else None
        }


# Global instance for easy access
session_manager = SessionManager()

# Set the global conversation_manager instance in the conversation_manager module
# to be the same instance used by the session manager
# This ensures consistency between direct access and session manager access
try:
    conversation_manager_module = sys.modules['core.conversation_manager']
    conversation_manager_module.conversation_manager = session_manager.conversation_manager
except Exception:
    # If there's an issue setting the global reference, continue anyway
    # The session manager will still work correctly
    pass