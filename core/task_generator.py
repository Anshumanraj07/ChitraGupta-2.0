"""
Task Generator Module for ChitraGupta 2.0
Generates tiny, concrete, actionable tasks based on discovered goals and struggles.
Follows the principle: dream big → break small → act now
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
from .goal_discovery import DiscoveredElements, GoalArea


class TaskPriority(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskDiscipline(Enum):
    MENTAL = "mental"
    PHYSICAL = "physical"
    HYBRID = "hybrid"


@dataclass
class GeneratedTask:
    title: str
    sub_tasks: List[str]
    execution_tips: List[str]
    priority: TaskPriority
    discipline: TaskDiscipline
    estimated_time_minutes: int
    confidence: float


class TaskGenerator:
    def __init__(self):
        # Task templates for different goal areas and struggles
        self.task_templates = {
            GoalArea.FITNESS: {
                "weight_loss": {
                    "title": "Walk for 10 minutes",
                    "sub_tasks": ["Put on walking shoes", "Walk outside or on treadmill for 10 minutes", "Track time completed"],
                    "execution_tips": ["Start with just 5 minutes if 10 feels too much", "Do it at the same time daily", "Listen to music or podcast to make it enjoyable"],
                    "priority": TaskPriority.MEDIUM,
                    "discipline": TaskDiscipline.PHYSICAL,
                    "estimated_time_minutes": 10
                },
                "exercise_start": {
                    "title": "Do 2 minutes of stretching",
                    "sub_tasks": ["Stand up from your chair", "Do neck rolls, shoulder rolls, and side stretches for 2 minutes", "Breathe deeply during stretches"],
                    "execution_tips": ["Do this after sitting for 30 minutes", "Set a reminder if needed", "Focus on breathing, not perfection"],
                    "priority": TaskPriority.LOW,
                    "discipline": TaskDiscipline.PHYSICAL,
                    "estimated_time_minutes": 2
                }
            },
            GoalArea.CAREER: {
                "skill_learning": {
                    "title": "Watch one 10-minute tutorial video",
                    "sub_tasks": ["Choose a skill you want to learn", "Find a 10-minute tutorial on YouTube or similar platform", "Watch and take one note"],
                    "execution_tips": ["Pick something immediately applicable", "Watch during a natural break in your day", "Apply what you learned within 24 hours"],
                    "priority": TaskPriority.MEDIUM,
                    "discipline": TaskDiscipline.MENTAL,
                    "estimated_time_minutes": 10
                },
                "networking": {
                    "title": "Send one professional message",
                    "sub_tasks": ["Think of one professional contact you haven't spoken to recently", "Send a brief, genuine message asking how they're doing", "Keep it under 3 sentences"],
                    "execution_tips": ["Don't ask for anything in return", "Personalize the message", "Send during business hours"],
                    "priority": TaskPriority.MEDIUM,
                    "discipline": TaskDiscipline.MENTAL,
                    "estimated_time_minutes": 5
                }
            },
            GoalArea.DISCIPLINE: {
                "routine_building": {
                    "title": "Do one thing at the same time today",
                    "sub_tasks": ["Choose one small daily action (like drinking water after brushing)", "Do it at the same time as your anchor habit", "Mark it done on a calendar or note"],
                    "execution_tips": ["Start ridiculous small (1 push-up, 1 glass of water)", "Attach it to an existing habit", "Don't break the chain"],
                    "priority": TaskPriority.HIGH,
                    "discipline": TaskDiscipline.HYBRID,
                    "estimated_time_minutes": 2
                },
                "focus_training": {
                    "title": "Work on one task for 5 minutes without distraction",
                    "sub_tasks": ["Choose one small work task", "Turn off notifications for 5 minutes", "Work continuously until timer ends"],
                    "execution_tips": ["Use a physical timer", "Start with 2 minutes if 5 feels impossible", "Notice the urge to distract and let it pass"],
                    "priority": TaskPriority.MEDIUM,
                    "discipline": TaskDiscipline.MENTAL,
                    "estimated_time_minutes": 5
                }
            },
            GoalArea.FINANCES: {
                "expense_tracking": {
                    "title": "Write down one expense you made today",
                    "sub_tasks": ["Think of something you spent money on today", "Write down what it was and how much it cost", "Note whether it was a need or want"],
                    "execution_tips": ["Do this right after spending if possible", "Keep it simple - no need for categories yet", "Just build the awareness habit"],
                    "priority": TaskPriority.LOW,
                    "discipline": TaskDiscipline.MENTAL,
                    "estimated_time_minutes": 2
                },
                "saving_start": {
                    "title": "Put aside 1% of what you earned today",
                    "sub_tasks": ["Calculate 1% of your income or expected income today", "Physically move that amount to a separate place", "Label it as 'savings'"],
                    "execution_tips": ["Start with literal pocket change if needed", "Make it automatic if possible", "Celebrate the act of saving, not the amount"],
                    "priority": TaskPriority.MEDIUM,
                    "discipline": TaskDiscipline.MENTAL,
                    "estimated_time_minutes": 3
                }
            },
            GoalArea.MENTAL_HEALTH: {
                "mindfulness_minute": {
                    "title": "Take one mindful breath",
                    "sub_tasks": ["Pause what you're doing", "Take one slow, deep breath in through nose", "Exhale slowly through mouth, noticing the sensation"],
                    "execution_tips": ["Set a phone reminder for random times", "Do it before answering phone unlocking to social media", "No need to close eyes or change posture"],
                    "priority": TaskPriority.LOW,
                    "discipline": TaskDiscipline.MENTAL,
                    "estimated_time_minutes": 1
                },
                "gratitude_moment": {
                    "title": "Think of one thing you're grateful for right now",
                    "sub_tasks": ["Pause for 10 seconds", "Think of one specific thing, person, or moment you appreciate", "Let yourself feel the gratitude for 5 seconds"],
                    "execution_tips": ["Be specific (not just 'my family' but 'my sister's laugh today')", "Do this when you feel stressed", "No need to write it down"],
                    "priority": TaskPriority.LOW,
                    "discipline": TaskDiscipline.MENTAL,
                    "estimated_time_minutes": 1
                }
            },
            GoalArea.LEARNING: {
                "micro_learning": {
                    "title": "Read one paragraph from a book or article",
                    "sub_tasks": ["Open a book or article you've been meaning to read", "Read just one paragraph", "Close it and reflect on one idea from it"],
                    "execution_tips": ["Keep the book/article in a visible place", "Choose something enjoyable, not obligatory", "One paragraph is enough to start"],
                    "priority": TaskPriority.LOW,
                    "discipline": TaskDiscipline.MENTAL,
                    "estimated_time_minutes": 2
                }
            }
        }
        
        # Default templates for when we don't have a specific match
        self.default_templates = {
            "general_improvement": {
                "title": "Do one small thing toward your goal today",
                "sub_tasks": ["Identify your current goal or area for improvement", "Think of the smallest possible action you could take", "Do that action right now"],
                "execution_tips": ["If you can't think of an action, just gather information for 5 minutes", "Make it so small it's almost ridiculous", "Focus on consistency, not magnitude"],
                "priority": TaskPriority.MEDIUM,
                "discipline": TaskDiscipline.HYBRID,
                "estimated_time_minutes": 5
            },
            "exploration": {
                "title": "Spend 5 minutes exploring your interest",
                "sub_tasks": ["Think about what topic or activity interests you lately", "Spend 5 minutes reading, watching, or thinking about it", "Note one thing you learned"],
                "execution_tips": ["Follow curiosity, not obligation", "Set a timer so you don't get lost", "Allow yourself to change topics"],
                "priority": TaskPriority.LOW,
                "discipline": TaskDiscipline.MENTAL,
                "estimated_time_minutes": 5
            }
        }
    
    def generate_task(self, discovered: DiscoveredElements, context: Dict[str, Any] = None) -> Optional[GeneratedTask]:
        """
        Generate a tiny, concrete task based on discovered elements.
        Returns None if confidence is too low or no appropriate task can be generated.
        """
        if context is None:
            context = {}
            
        # Only generate task if we have reasonable confidence
        if discovered.confidence < 0.5:
            return None
            
        # Determine which template to use
        template_key = self._select_template(discovered)
        
        # Get the template
        template = None
        if discovered.goal_area and discovered.goal_area in self.task_templates:
            area_templates = self.task_templates[discovered.goal_area]
            # Try to find a specific template based on struggle or goal
            if discovered.struggle:
                struggle_key = self._match_to_template_key(discovered.struggle.lower())
                if struggle_key in area_templates:
                    template = area_templates[struggle_key]
            if not template and discovered.goal:
                goal_key = self._match_to_template_key(discovered.goal.lower())
                if goal_key in area_templates:
                    template = area_templates[goal_key]
        
        # Fall back to area-general template if available
        if not template and discovered.goal_area:
            # Use first available template in the area as fallback
            area_templates = self.task_templates.get(discovered.goal_area, {})
            if area_templates:
                template = list(area_templates.values())[0]
        
        # Fall back to default templates
        if not template:
            if discovered.goal or discovered.struggle or discovered.habit or discovered.routine:
                template_key = self._select_default_template(discovered)
                template = self.default_templates.get(template_key, self.default_templates["general_improvement"])
            else:
                return None  # Not enough clear discovery to generate a task
        
        # Generate the task from template
        task = GeneratedTask(
            title=template["title"],
            sub_tasks=template["sub_tasks"].copy(),
            execution_tips=template["execution_tips"].copy(),
            priority=template["priority"],
            discipline=template["discipline"],
            estimated_time_minutes=template["estimated_time_minutes"],
            confidence=discovered.confidence
        )
        
        # Personalize the task based on discovered elements
        task = self._personalize_task(task, discovered)
        
        return task
    
    def _select_template(self, discovered: DiscoveredElements) -> str:
        """Select the most appropriate template based on discovered elements."""
        # Priority: struggle > goal > goal_area
        if discovered.struggle:
            struggle_key = self._match_to_template_key(discovered.struggle.lower())
            if discovered.goal_area and discovered.goal_area in self.task_templates:
                if struggle_key in self.task_templates[discovered.goal_area]:
                    return struggle_key
        
        if discovered.goal:
            goal_key = self._match_to_template_key(discovered.goal.lower())
            if discovered.goal_area and discovered.goal_area in self.task_templates:
                if goal_key in self.task_templates[discovered.goal_area]:
                    return goal_key
        
        # Fall back to goal area
        if discovered.goal_area and discovered.goal_area in self.task_templates:
            return list(self.task_templates[discovered.goal_area].keys())[0] if self.task_templates[discovered.goal_area] else "general_improvement"
        
        return "general_improvement"
    
    def _select_default_template(self, discovered: DiscoveredElements) -> str:
        """Select default template when no specific area match."""
        if discovered.struggle:
            if any(word in discovered.struggle.lower() for word in ["focus", "distract", "procrastinat"]):
                return "exploration"
            elif any(word in discovered.struggle.lower() for word in ["stress", "anxious", "overwhelm"]):
                return "exploration"
        
        return "general_improvement"
    
    def _match_to_template_key(self, text: str) -> str:
        """Match text to a template key using keyword matching."""
        text_lower = text.lower()
        
        # Fitness keywords
        if any(word in text_lower for word in ["weight", "fat", "lose"]):
            return "weight_loss"
        if any(word in text_lower for word in ["exercise", "workout", "fit", "gym"]):
            return "exercise_start"
            
        # Career keywords
        if any(word in text_lower for word in ["skill", "learn", "course", "study"]):
            return "skill_learning"
        if any(word in text_lower for word in ["job", "work", "career", "network"]):
            return "networking"
            
        # Discipline keywords
        if any(word in text_lower for word in ["habit", "routine", "consistent", "daily"]):
            return "routine_building"
        if any(word in text_lower for word in ["focus", "distract", "procrastinat"]):
            return "focus_training"
            
        # Finance keywords
        if any(word in text_lower for word in ["money", "save", "budget", "expense"]):
            return "expense_tracking"
        if any(word in text_lower for word in ["save", "invest", "wealth"]):
            return "saving_start"
            
        # Mental health keywords
        if any(word in text_lower for word in ["stress", "anxious", "calm", "mind"]):
            return "mindfulness_minute"
        if any(word in text_lower for word in ["grateful", "thankful", "appreciate"]):
            return "gratitude_moment"
            
        # Learning keywords
        if any(word in text_lower for word in ["learn", "read", "study", "course"]):
            return "micro_learning"
            
        return "general_improvement"
    
    def _personalize_task(self, task: GeneratedTask, discovered: DiscoveredElements) -> GeneratedTask:
        """Personalize the task template based on discovered elements."""
        # Customize title if we have specific goal/struggle info
        if discovered.goal and len(discovered.goal) < 50:  # Not too long
            if "your goal" in task.title.lower():
                task.title = task.title.replace("your goal", discovered.goal)
            elif "toward your goal" in task.title.lower():
                task.title = f"Do one small thing toward {discovered.goal.lower()} today"
                
        if discovered.struggle and len(discovered.struggle) < 50:
            if "your struggle" in task.title.lower():
                task.title = task.title.replace("your struggle", discovered.struggle)
        
        # Add context-specific tips
        if discovered.habit:
            tip = f"Try connecting this to your existing habit of: {discovered.habit}"
            if tip not in task.execution_tips:
                task.execution_tips.insert(0, tip)
                
        if discovered.routine:
            tip = f"Consider doing this at the same time as your routine of: {discovered.routine}"
            if tip not in task.execution_tips:
                task.execution_tips.insert(0, tip)
                
        # Ensure we don't have too many tips
        if len(task.execution_tips) > 5:
            task.execution_tips = task.execution_tips[:5]
            
        return task


# Global instance for easy access
task_generator = TaskGenerator()