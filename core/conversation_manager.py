"""
Conversation Manager Module for ChitraGupta 2.0
Implements the state machine for onboarding, discovery, goal clarification, and task readiness.
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional


class ConversationState(Enum):
    ONBOARDING = "onboarding"        # First interaction, getting to know user
    DISCOVERY = "discovery"          # Exploring goals, struggles, habits
    GOAL_CLARIFIED = "goal_clarified" # Clear goal identified
    ACTION_READY = "action_ready"    # Ready to suggest a small action
    TASK_CREATED = "task_created"    # Just suggested a task
    DAILY_REVIEW = "daily_review"    # End-of-day reflection
    SUMMARY_COMPACTION = "summary_compaction" # Monthly summary


@dataclass
class ConversationContext:
    """Context gathered during conversation for task generation."""
    user_id: str = "default_user"
    goal: Optional[str] = None
    struggle: Optional[str] = None
    habit: Optional[str] = None
    routine: Optional[str] = None
    roadmap: Optional[str] = None
    conversation_count: int = 0
    last_interaction: datetime = field(default_factory=datetime.now)
    daily_summary_date: Optional[str] = None  # YYYY-MM-DD of last summary


class ConversationManager:
    def __init__(self, user_id: str = "default_user"):
        self.user_id = user_id
        self.state = ConversationState.ONBOARDING
        self.context = ConversationContext(user_id=user_id)
        self._daily_reset_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
    def update_state(self, user_input: str, context: Dict[str, Any] = None) -> ConversationState:
        """
        Update conversation state based on user input and context.
        Returns the new state.
        """
        if context is None:
            context = {}
            
        # Update basic context
        self.context.conversation_count += 1
        self.context.last_interaction = datetime.now()
        
        # Check for day boundary
        if self._is_new_day():
            self._handle_day_boundary()
            
        # State transition logic
        if self.state == ConversationState.ONBOARDING:
            self.state = self._handle_onboarding(user_input, context)
        elif self.state == ConversationState.DISCOVERY:
            self.state = self._handle_discovery(user_input, context)
        elif self.state == ConversationState.GOAL_CLARIFIED:
            self.state = self._handle_goal_clarified(user_input, context)
        elif self.state == ConversationState.ACTION_READY:
            self.state = self._handle_action_ready(user_input, context)
        elif self.state == ConversationState.TASK_CREATED:
            self.state = self._handle_task_created(user_input, context)
        elif self.state == ConversationState.DAILY_REVIEW:
            self.state = self._handle_daily_review(user_input, context)
        elif self.state == ConversationState.SUMMARY_COMPACTION:
            self.state = self._handle_summary_compaction(user_input, context)
            
        return self.state
        
    def _is_new_day(self) -> bool:
        """Check if we've crossed a day boundary."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return today > self._daily_reset_time
        
    def _handle_day_boundary(self):
        """Handle transition to a new day."""
        self._daily_reset_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        # In a full implementation, this would trigger daily summary creation
        # For now, we just reset to discovery for continuing conversation
        if self.state in [ConversationState.TASK_CREATED, ConversationState.DAILY_REVIEW]:
            self.state = ConversationState.DISCOVERY
            
    def _handle_onboarding(self, user_input: str, context: Dict[str, Any]) -> ConversationState:
        """Handle initial onboarding phase."""
        # Simple heuristic: if user shares anything beyond greeting, move to discovery
        user_input_lower = user_input.lower().strip()
        greetings = ["hi", "hello", "hey", "sup", "yo", "howdy"]
        
        # If it's just a greeting, stay in onboarding
        if any(user_input_lower.startswith(g) for g in greetings) and len(user_input.split()) <= 2:
            return ConversationState.ONBOARDING
            
        # Otherwise, move to discovery
        return ConversationState.DISCOVERY
        
    def _handle_discovery(self, user_input: str, context: Dict[str, Any]) -> ConversationState:
        """Handle discovery phase - extract goals, struggles, etc."""
        # In a full implementation, we'd use the goal discovery module here
        # For now, we'll use simple heuristics
        
        user_input_lower = user_input.lower()
        
        # Check if user expressed a clear goal or struggle
        goal_indicators = ["want", "need", "goal", "aim", "hope", "wish", "desire"]
        struggle_indicators = ["struggle", "problem", "difficulty", "hard", "can't", "difficult"]
        
        has_goal = any(indicator in user_input_lower for indicator in goal_indicators)
        has_struggle = any(indicator in user_input_lower for indicator in struggle_indicators)
        
        if has_goal or has_struggle:
            # Extract some basic info (in real implementation, use goal_discovery module)
            self._extract_basic_context(user_input)
            return ConversationState.GOAL_CLARIFIED
            
        return ConversationState.DISCOVERY
        
    def _handle_goal_clarified(self, user_input: str, context: Dict[str, Any]) -> ConversationState:
        """Handle when we have a preliminary goal/struggle."""
        user_input_lower = user_input.lower()
        
        # Check if user is providing more details about their situation
        detail_indicators = ["because", "since", "due to", "reason", "try", "tried", 
                           "habit", "routine", "daily", "always", "usually"]
        
        has_details = any(indicator in user_input_lower for indicator in detail_indicators)
        
        if has_details:
            self._extract_basic_context(user_input)
            # If we have enough detail, move to action ready
            if self._has_sufficient_context():
                return ConversationState.ACTION_READY
        elif any(word in user_input_lower for word in ["yes", "yeah", "yep", "correct", "right"]):
            # User confirming our understanding
            if self._has_sufficient_context():
                return ConversationState.ACTION_READY
                
        return ConversationState.GOAL_CLARIFIED
        
    def _handle_action_ready(self, user_input: str, context: Dict[str, Any]) -> ConversationState:
        """Handle when we're ready to suggest an action."""
        user_input_lower = user_input.lower()
        
        # Check if user is ready for a task or wants to explore more
        ready_indicators = ["yes", "sure", "ok", "okay", "let's do it", "sounds good", 
                          "what should i do", "give me a task", "suggest something"]
        explore_more = ["tell me more", "explain", "what do you mean", "how", "why"]
        
        if any(indicator in user_input_lower for indicator in ready_indicators):
            return ConversationState.TASK_CREATED
        elif any(indicator in user_input_lower for indicator in explore_more):
            return ConversationState.DISCOVERY  # Go back to exploration
            
        # Default: stay in action ready unless user seems disengaged
        disengaged = ["no", "not really", "maybe later", "idk", "i don't know"]
        if any(indicator in user_input_lower for indicator in disengaged):
            return ConversationState.DISCOVERY
            
        return ConversationState.ACTION_READY
        
    def _handle_task_created(self, user_input: str, context: Dict[str, Any]) -> ConversationState:
        """Handle after we've suggested a task."""
        user_input_lower = user_input.lower()
        
        # Check user response to the task
        positive = ["will do", "going to", "try", "yes", "sure", "ok", "thanks", "thank you"]
        negative = ["can't", "unable", "too hard", "not now", "later", "maybe"]
        done = ["did it", "done", "finished", "completed"]
        
        if any(indicator in user_input_lower for indicator in done):
            # User says they did it - could move to daily review or continue
            return ConversationState.DAILY_REVIEW
        elif any(indicator in user_input_lower for indicator in negative):
            # User rejected or hesitant - go back to discovery
            return ConversationState.DISCOVERY
        elif any(indicator in user_input_lower for indicator in ["more", "another", "else"]):
            # User wants another suggestion
            return ConversationState.ACTION_READY
            
        # Default: stay in task created state for a bit to see if they engage
        return ConversationState.TASK_CREATED
        
    def _handle_daily_review(self, user_input: str, context: Dict[str, Any]) -> ConversationState:
        """Handle end-of-day reflection."""
        # In a full implementation, this would trigger daily summary creation
        # For now, we'll just reset for next day
        user_input_lower = user_input.lower()
        
        if any(word in user_input_lower for word in ["tomorrow", "next day", "future"]):
            return ConversationState.ONBOARDING  # Start fresh next day
            
        return ConversationState.DAILY_REVIEW
        
    def _handle_summary_compaction(self, user_input: str, context: Dict[str, Any]) -> ConversationState:
        """Handle monthly summary compaction (every 30 days)."""
        # This would be triggered automatically based on date, not user input
        # For now, just return to discovery
        return ConversationState.DISCOVERY
        
    def _extract_basic_context(self, user_input: str):
        """Extract basic goal/struggle/habit from user input (simplified)."""
        user_input_lower = user_input.lower()
        
        # Very basic extraction - in reality, we'd use the goal_discovery module
        if "goal" in user_input_lower or "want" in user_input_lower or "need" in user_input_lower:
            # Extract simple goal statement
            import re
            # Look for patterns like "I want to X" or "My goal is to X"
            patterns = [
                r"i\s+(?:want|need|would\s+like)\s+to\s+(.+)",
                r"my\s+goal\s+is\s+to\s+(.+)",
                r"i\s+(?:hope|plan|aim)\s+to\s+(.+)"
            ]
            for pattern in patterns:
                match = re.search(pattern, user_input_lower)
                if match:
                    self.context.goal = match.group(1).strip()
                    break
                    
        if "struggle" in user_input_lower or "difficult" in user_input_lower or "hard" in user_input_lower:
            patterns = [
                r"i\s+(?:struggle|have\s+trouble\s+with|find\s+it\s+hard)\s+(.+)",
                r"(?:it\'s|that\'s)\s+(?:hard|difficult|tough)\s+to\s+(.+)"
            ]
            for pattern in patterns:
                match = re.search(pattern, user_input_lower)
                if match:
                    self.context.struggle = match.group(1).strip()
                    break
                    
        if "habit" in user_input_lower or "usually" in user_input_lower or "always" in user_input_lower:
            patterns = [
                r"i\s+(?:usually|always|typically)\s+(.+)",
                r"my\s+habit\s+is\s+to\s+(.+)",
                r"i\s+have\s+a\s+habit\s+of\s+(.+)"
            ]
            for pattern in patterns:
                match = re.search(pattern, user_input_lower)
                if match:
                    self.context.habit = match.group(1).strip()
                    break
                    
    def _has_sufficient_context(self) -> bool:
        """Check if we have enough context to suggest a task."""
        # We need at least a goal or struggle, and preferably some context
        has_core = bool(self.context.goal or self.context.struggle)
        has_context = bool(self.context.habit or self.context.routine or 
                         len([x for x in [self.context.goal, self.context.struggle] if x]) >= 2)
        return has_core and (has_context or self.context.conversation_count >= 3)
        
    def should_create_task(self) -> bool:
        """Determine if we should create a task based on current state and context."""
        # Only create a task in ACTION_READY state with sufficient context
        if self.state != ConversationState.ACTION_READY:
            return False
            
        return self._has_sufficient_context()
        
    def get_context_for_task_generation(self) -> Dict[str, Any]:
        """Get context information for task generation."""
        return {
            "goal": self.context.goal,
            "struggle": self.context.struggle,
            "habit": self.context.habit,
            "routine": self.context.routine,
            "roadmap": self.context.roadmap,
            "conversation_count": self.context.conversation_count,
            "user_id": self.context.user_id
        }
        
    def reset_for_new_day(self):
        """Reset state for a new day (called by session manager)."""
        # Keep the core goal/struggle/etc. for continuity but reset conversation count
        self.context.conversation_count = 0
        self.context.last_interaction = datetime.now()
        # If we were in a terminal state, go back to discovery
        if self.state in [ConversationState.TASK_CREATED, ConversationState.DAILY_REVIEW]:
            self.state = ConversationState.DISCOVERY
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert current state to dictionary for serialization."""
        return {
            "user_id": self.context.user_id,
            "state": self.state.value,
            "goal": self.context.goal,
            "struggle": self.context.struggle,
            "habit": self.context.habit,
            "routine": self.context.routine,
            "roadmap": self.context.roadmap,
            "conversation_count": self.context.conversation_count,
            "last_interaction": self.context.last_interaction.isoformat(),
            "daily_summary_date": self.context.daily_summary_date
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationManager':
        """Create ConversationManager from dictionary."""
        obj = cls(user_id=data.get("user_id", "default_user"))
        obj.state = ConversationState(data.get("state", ConversationState.ONBOARDING.value))
        obj.context.goal = data.get("goal")
        obj.context.struggle = data.get("struggle")
        obj.context.habit = data.get("habit")
        obj.context.routine = data.get("routine")
        obj.context.roadmap = data.get("roadmap")
        obj.context.conversation_count = data.get("conversation_count", 0)
        if data.get("last_interaction"):
            obj.context.last_interaction = datetime.fromisoformat(data["last_interaction"])
        obj.context.daily_summary_date = data.get("daily_summary_date")
        return obj


# Global instance for easy access
conversation_manager = ConversationManager()