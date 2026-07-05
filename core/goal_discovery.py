"""
Goal Discovery Module for ChitraGupta 2.0
Extracts goals, struggles, habits, and routines from conversation using deterministic rules and lightweight NLP.
"""

import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class GoalArea(Enum):
    FITNESS = "fitness"
    CAREER = "career"
    DISCIPLINE = "discipline"
    FINANCES = "finances"
    RELATIONSHIPS = "relationships"
    MENTAL_HEALTH = "mental_health"
    LEARNING = "learning"
    OTHER = "other"


@dataclass
class DiscoveredElements:
    goal: Optional[str] = None
    struggle: Optional[str] = None
    habit: Optional[str] = None
    routine: Optional[str] = None
    roadmap: Optional[str] = None
    goal_area: Optional[GoalArea] = None
    confidence: float = 0.0


class GoalDiscovery:
    def __init__(self):
        # Keywords for goal area detection
        self.goal_area_keywords = {
            GoalArea.FITNESS: [
                "fitness", "exercise", "workout", "gym", "weight", "run", "running",
                "jog", "yoga", "strength", "muscle", "body", "health", "diet", "eat"
            ],
            GoalArea.CAREER: [
                "career", "job", "work", "promotion", "salary", "skill", "learn",
                "professional", "business", "interview", "resume", "linkedin"
            ],
            GoalArea.DISCIPLINE: [
                "discipline", "habit", "routine", "consistent", "daily", "regular",
                "schedule", "time management", "productivity", "focus", "distraction"
            ],
            GoalArea.FINANCES: [
                "money", "finance", "budget", "save", "invest", "debt", "loan",
                "expense", "income", "salary", "wealth", "financial"
            ],
            GoalArea.RELATIONSHIPS: [
                "relationship", "friend", "family", "partner", "love", "social",
                "talk", "communicate", "conflict", "trust"
            ],
            GoalArea.MENTAL_HEALTH: [
                "stress", "anxiety", "depression", "mental", "mind", "calm",
                "meditation", "therapy", "emotion", "feel", "mood"
            ],
            GoalArea.LEARNING: [
                "learn", "study", "course", "book", "read", "skill", "knowledge",
                "education", "class", "training", "tutorial"
            ]
        }
        
        # Patterns for extracting different elements
        self.goal_patterns = [
            r"(?:i\s+)?(?:want|need|would\s+like|aim\s+to|goal\s+is)\s+(.+?)(?:\.|$)",
            r"(?:my\s+)?(?:goal|objective|target)\s+is\s+(.+?)(?:\.|$)",
            r"(?:i\s+)?(?:hope\s+to|plan\s+to|intend\s+to)\s+(.+?)(?:\.|$)"
        ]
        
        self.struggle_patterns = [
            r"(?:i\s+)?(?:struggle|problem|difficulty|issue|challenge)\s+with\s+(.+?)(?:\.|$)",
            r"(?:i\s+)?(?:can't|cannot|hard\s+to|difficult\s+to)\s+(.+?)(?:\.|$)",
            r"(?:i\s+)?(?:find\s+it\s+hard|trouble\s+with)\s+(.+?)(?:\.|$)"
        ]
        
        self.habit_patterns = [
            r"(?:i\s+)?(?:habit|routine|usually|always|typically|every\s+day)\s+(.+?)(?:\.|$)",
            r"(?:i\s+)?(?:keep\s+doing|tend\s+to|tend\s+to\s+do)\s+(.+?)(?:\.|$)"
        ]
        
    def discover(self, user_input: str, context: Dict[str, Any] = None) -> DiscoveredElements:
        """
        Discover goals, struggles, habits, and routines from user input.
        Uses regex patterns and keyword matching for deterministic extraction.
        """
        if context is None:
            context = {}
            
        elements = DiscoveredElements()
        user_input_lower = user_input.lower().strip()
        
        # Extract goal
        elements.goal = self._extract_using_patterns(user_input, self.goal_patterns)
        if not elements.goal:
            # Fallback: look for goal-like statements
            elements.goal = self._extract_goal_fallback(user_input)
            
        # Extract struggle
        elements.struggle = self._extract_using_patterns(user_input, self.struggle_patterns)
        
        # Extract habit/routine
        elements.habit = self._extract_using_patterns(user_input, self.habit_patterns)
        if not elements.habit:
            elements.routine = self._extract_using_patterns(user_input, self.habit_patterns)  # Reuse patterns
            
        # Determine goal area
        elements.goal_area = self._detect_goal_area(user_input_lower)
        
        # Calculate confidence based on what we found
        elements.confidence = self._calculate_confidence(elements)
        
        return elements
        
    def _extract_using_patterns(self, text: str, patterns: List[str]) -> Optional[str]:
        """Extract information using regex patterns."""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                extracted = match.group(1).strip()
                # Clean up common artifacts
                extracted = re.sub(r'^\s+(to\s+|for\s+|me\s+)', '', extracted)
                if len(extracted) > 3:  # Avoid extracting too short phrases
                    return extracted
        return None
        
    def _extract_goal_fallback(self, text: str) -> Optional[str]:
        """Fallback method to extract goal when patterns don't match."""
        # Look for sentences with goal-oriented verbs
        goal_verbs = ["want", "need", "desire", "hope", "plan", "aim", "intend"]
        sentences = re.split(r'[.!?]+', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if any(verb in sentence.lower() for verb in goal_verbs):
                # Clean up the sentence
                cleaned = re.sub(r'\b(i\s+|we\s+|they\s+)', '', sentence, flags=re.IGNORECASE)
                cleaned = cleaned.strip()
                if len(cleaned) > 5:
                    return cleaned
        return None
        
    def _detect_goal_area(self, text: str) -> Optional[GoalArea]:
        """Detect which goal area the input relates to based on keywords."""
        scores = {}
        for area, keywords in self.goal_area_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                scores[area] = score
                
        if scores:
            return max(scores, key=scores.get)
        return GoalArea.OTHER
        
    def _calculate_confidence(self, elements: DiscoveredElements) -> float:
        """Calculate confidence score based on discovered elements."""
        score = 0.0
        max_score = 4.0  # goal, struggle, habit, goal_area
        
        if elements.goal:
            score += 1.0
        if elements.struggle:
            score += 1.0
        if elements.habit or elements.routine:
            score += 1.0
        if elements.goal_area and elements.goal_area != GoalArea.OTHER:
            score += 1.0
            
        return score / max_score if max_score > 0 else 0.0
        
    def get_discovery_summary(self, elements: DiscoveredElements) -> str:
        """Get a human-readable summary of what was discovered."""
        parts = []
        if elements.goal:
            parts.append(f"Goal: {elements.goal}")
        if elements.struggle:
            parts.append(f"Struggle: {elements.struggle}")
        if elements.habit:
            parts.append(f"Habit: {elements.habit}")
        if elements.routine:
            parts.append(f"Routine: {elements.routine}")
        if elements.goal_area:
            parts.append(f"Area: {elements.goal_area.value}")
            
        return " | ".join(parts) if parts else "No clear elements discovered"


# Global instance for easy access
goal_discovery = GoalDiscovery()