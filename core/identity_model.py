"""
ChitraGupta 2.0 — Identity Model
Persistent user identity tracking with incremental updates from evidence.
"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, date
from collections import defaultdict

from core.schemas.identity import (
    IdentityProfile, IdentityEvidence, IdentityUpdate, SelfImageSnapshot,
    MotivationStyle, DisciplinePattern, EnergyPattern, LearningStyle,
    CommunicationPreference, CoachingPreference
)
from core.utils.supabase_client import get_supabase_client

logger = logging.getLogger("chitragupta.identity_model")


class IdentityModel:
    """
    Manages persistent user identity with incremental, evidence-based updates.
    Stores in Supabase, updates only when sufficient evidence accumulates.
    """
    
    def __init__(self, user_id: str = "default_user"):
        self.user_id = user_id
        self.profile: Optional[IdentityProfile] = None
        self._pending_evidence: List[IdentityEvidence] = []
        self._evidence_threshold = 3  # Min evidence pieces before updating
        self._confidence_threshold = 0.6  # Min confidence to update
        self._load_profile()
    
    def _load_profile(self):
        """Load identity profile from Supabase."""
        try:
            supabase = get_supabase_client()
            if supabase:
                response = supabase.table("user_identities").select("*").eq("user_id", self.user_id).execute()
                if response.data:
                    data = response.data[0]
                    # Convert stored JSON back to profile
                    self.profile = IdentityProfile(**data)
                    logger.info(f"Loaded identity profile for {self.user_id} (v{self.profile.version})")
                    return
        except Exception as e:
            logger.warning(f"Failed to load identity from Supabase: {e}")
        
        # Create new profile
        self.profile = IdentityProfile(user_id=self.user_id)
        logger.info(f"Created new identity profile for {self.user_id}")
    
    def _save_profile(self):
        """Save identity profile to Supabase."""
        try:
            supabase = get_supabase_client()
            if supabase and self.profile:
                self.profile.updated_at = datetime.utcnow()
                data = self.profile.model_dump()
                # Convert datetime to ISO string for Supabase
                data["created_at"] = self.profile.created_at.isoformat()
                data["updated_at"] = self.profile.updated_at.isoformat()
                
                supabase.table("user_identities").upsert(data, on_conflict="user_id").execute()
                logger.debug(f"Saved identity profile for {self.user_id} (v{self.profile.version})")
        except Exception as e:
            logger.error(f"Failed to save identity to Supabase: {e}")
    
    def add_evidence(self, evidence: IdentityEvidence):
        """Add evidence and trigger incremental update if threshold met."""
        self._pending_evidence.append(evidence)
        
        # Group by category and check thresholds
        by_category = defaultdict(list)
        for ev in self._pending_evidence:
            by_category[ev.category].append(ev)
        
        for category, evidences in by_category.items():
            if len(evidences) >= self._evidence_threshold:
                self._process_category_evidence(category, evidences)
    
    def _process_category_evidence(self, category: str, evidences: List[IdentityEvidence]):
        """Process accumulated evidence for a category."""
        # Calculate weighted average confidence
        total_weight = sum(e.confidence for e in evidences)
        if total_weight == 0:
            return
        
        # Extract proposed values from evidence
        proposed_values = []
        for ev in evidences:
            if category in ["values", "beliefs", "goals", "fears", "strengths", "weaknesses"]:
                # For list fields, extract items from content
                items = self._extract_items_from_evidence(ev.content, category)
                proposed_values.extend([(item, ev.confidence) for item in items])
            else:
                # For enum fields, infer from content
                proposed = self._infer_enum_value(category, ev.content)
                if proposed:
                    proposed_values.append((proposed, ev.confidence))
        
        if not proposed_values:
            return
        
        # Aggregate by proposed value
        value_scores = defaultdict(float)
        for value, conf in proposed_values:
            value_scores[value] += conf
        
        # Get top proposed value
        top_value = max(value_scores.items(), key=lambda x: x[1])
        proposed_value, confidence = top_value
        confidence = confidence / total_weight
        
        if confidence < self._confidence_threshold:
            return
        
        # Generate update
        current_value = self._get_current_value(category)
        if current_value == proposed_value:
            # Same value, just increase confidence
            self._increase_confidence(category, confidence)
            return
        
        update = IdentityUpdate(
            category=category,
            field=category,
            current_value=current_value,
            proposed_value=proposed_value,
            confidence=confidence,
            evidence=evidences,
            reasoning=f"Accumulated {len(evidences)} pieces of evidence"
        )
        
        self._apply_update(update)
        
        # Clear processed evidence
        self._pending_evidence = [e for e in self._pending_evidence if e.category != category]
    
    def _extract_items_from_evidence(self, content: str, category: str) -> List[str]:
        """Extract discrete items from evidence content."""
        # Simple extraction - in practice could use NLP
        items = []
        content_lower = content.lower()
        
        # Common patterns for each category
        patterns = {
            "values": ["value", "important to me", "care about", "believe in"],
            "beliefs": ["believe", "think that", "convinced that", "know that"],
            "goals": ["want to", "goal is", "aim to", "hope to", "trying to"],
            "fears": ["afraid of", "fear", "worried about", "scared of", "anxious about"],
            "strengths": ["good at", "strength", "excel at", "strong in"],
            "weaknesses": ["bad at", "weakness", "struggle with", "difficult for me"],
        }
        
        # Extract sentences containing patterns
        for pattern in patterns.get(category, []):
            if pattern in content_lower:
                # Take the sentence containing the pattern
                sentences = content.split(".")
                for sent in sentences:
                    if pattern in sent.lower():
                        items.append(sent.strip())
        
        return items[:3]  # Limit
    
    def _infer_enum_value(self, category: str, content: str) -> Optional[str]:
        """Infer enum value from content."""
        content_lower = content.lower()
        
        if category == "motivation_style":
            if any(w in content_lower for w in ["intrinsic", "internal", "for myself", "personal satisfaction"]):
                return MotivationStyle.INTRINSIC.value
            if any(w in content_lower for w in ["external", "reward", "recognition", "praise", "money"]):
                return MotivationStyle.EXTRINSIC.value
            if any(w in content_lower for w in ["social", "others", "people", "community", "together"]):
                return MotivationStyle.SOCIAL.value
            if any(w in content_lower for w in ["achieve", "accomplish", "win", "succeed", "best"]):
                return MotivationStyle.ACHIEVEMENT.value
            if any(w in content_lower for w in ["master", "learn", "improve", "grow", "develop"]):
                return MotivationStyle.MASTERY.value
            if any(w in content_lower for w in ["autonomy", "freedom", "choice", "control", "own way"]):
                return MotivationStyle.AUTONOMY.value
            if any(w in content_lower for w in ["purpose", "meaning", "mission", "calling", "contribute"]):
                return MotivationStyle.PURPOSE.value
        
        elif category == "discipline_pattern":
            if any(w in content_lower for w in ["consistent", "every day", "regular", "routine", "steady"]):
                return DisciplinePattern.CONSISTENT.value
            if any(w in content_lower for w in ["sporadic", "sometimes", "when i can", "irregular"]):
                return DisciplinePattern.SPORADIC.value
            if any(w in content_lower for w in ["burst", "intense", "all at once", "marathon", "sprint"]):
                return DisciplinePattern.BURST.value
            if any(w in content_lower for w in ["procrastinat", "put off", "delay", "later", "tomorrow"]):
                return DisciplinePattern.PROCRASTINATOR.value
            if any(w in content_lower for w in ["perfect", "exactly right", "flawless", "just right"]):
                return DisciplinePattern.PERFECTIONIST.value
            if any(w in content_lower for w in ["all or nothing", "everything", "completely", "fully"]):
                return DisciplinePattern.ALL_OR_NOTHING.value
            if any(w in content_lower for w in ["gradual", "slow", "step by step", "incremental", "little by little"]):
                return DisciplinePattern.GRADUAL.value
        
        elif category == "energy_pattern":
            if any(w in content_lower for w in ["morning", "early", "dawn", "am person", "wake up"]):
                return EnergyPattern.MORNING.value
            if any(w in content_lower for w in ["afternoon", "midday", "lunch"]):
                return EnergyPattern.AFTERNOON.value
            if any(w in content_lower for w in ["evening", "night", "late", "pm person", "owl"]):
                return EnergyPattern.EVENING.value if "evening" in content_lower else EnergyPattern.NIGHT.value
            if any(w in content_lower for w in ["varies", "depends", "sometimes", "different"]):
                return EnergyPattern.VARIABLE.value
        
        return None
    
    def _get_current_value(self, category: str) -> Any:
        """Get current value for a category."""
        if not self.profile:
            return None
        
        if category in ["values", "beliefs", "goals", "fears", "strengths", "weaknesses"]:
            return getattr(self.profile, category, [])
        elif category == "motivation_style":
            return self.profile.motivation_style.value
        elif category == "discipline_pattern":
            return self.profile.discipline_pattern.value
        elif category == "energy_pattern":
            return self.profile.energy_pattern.value
        elif category == "learning_style":
            return self.profile.learning_style.value
        elif category == "communication_preference":
            return self.profile.communication_preference.value
        elif category == "coaching_preference":
            return self.profile.coaching_preference.value
        
        return None
    
    def _apply_update(self, update: IdentityUpdate):
        """Apply an identity update to the profile."""
        if not self.profile:
            return
        
        category = update.category
        proposed = update.proposed_value
        confidence = update.confidence
        
        if category in ["values", "beliefs", "goals", "fears", "strengths", "weaknesses"]:
            # Add to list if not present
            current_list = getattr(self.profile, category, [])
            if isinstance(proposed, list):
                for item in proposed:
                    if item not in current_list:
                        current_list.append(item)
            elif proposed not in current_list:
                current_list.append(proposed)
            setattr(self.profile, category, current_list)
            
        elif category == "motivation_style":
            self.profile.motivation_style = MotivationStyle(proposed)
        elif category == "discipline_pattern":
            self.profile.discipline_pattern = DisciplinePattern(proposed)
        elif category == "energy_pattern":
            self.profile.energy_pattern = EnergyPattern(proposed)
        elif category == "learning_style":
            self.profile.learning_style = LearningStyle(proposed)
        elif category == "communication_preference":
            self.profile.communication_preference = CommunicationPreference(proposed)
        elif category == "coaching_preference":
            self.profile.coaching_preference = CoachingPreference(proposed)
        
        # Update confidence scores
        self._increase_confidence(category, confidence)
        
        # Increment version
        self.profile.version += 1
        self.profile.evidence_count[category] = self.profile.evidence_count.get(category, 0) + len(update.evidence)
        
        # Save
        self._save_profile()
        
        logger.info(f"Identity updated: {category} -> {proposed} (confidence: {confidence:.2f}, v{self.profile.version})")
    
    def _increase_confidence(self, category: str, amount: float):
        """Increase confidence score for a category."""
        if not self.profile:
            return
        current = self.profile.confidence_scores.get(category, 0.0)
        self.profile.confidence_scores[category] = min(1.0, current + amount * 0.5)
    
    def add_self_image_snapshot(self, assessment: str, confidence: float = 0.7):
        """Add a self-image snapshot from user reflection."""
        if not self.profile:
            return
        
        snapshot = SelfImageSnapshot(
            date=date.today().isoformat(),
            self_assessment=assessment,
            confidence=confidence,
            key_themes=self._extract_themes(assessment)
        )
        
        self.profile.self_image_trajectory.append(snapshot.model_dump())
        # Keep last 50 snapshots
        if len(self.profile.self_image_trajectory) > 50:
            self.profile.self_image_trajectory = self.profile.self_image_trajectory[-50:]
        
        self.profile.version += 1
        self._save_profile()
    
    def _extract_themes(self, text: str) -> List[str]:
        """Extract key themes from self-assessment text."""
        # Simple keyword extraction
        themes = []
        text_lower = text.lower()
        theme_keywords = {
            "growth": ["grow", "improve", "develop", "learn", "better"],
            "discipline": ["discipline", "consistent", "routine", "habit", "control"],
            "health": ["health", "fit", "exercise", "strong", "energy"],
            "career": ["career", "work", "job", "professional", "success"],
            "relationships": ["relationship", "family", "friend", "connect", "love"],
            "creativity": ["creative", "create", "art", "write", "make", "build"],
            "peace": ["peace", "calm", "balance", "centered", "mindful"],
            "achievement": ["achieve", "accomplish", "goal", "reach", "complete"],
        }
        
        for theme, keywords in theme_keywords.items():
            if any(kw in text_lower for kw in keywords):
                themes.append(theme)
        
        return themes[:5]
    
    def get_profile_summary(self) -> Dict[str, Any]:
        """Get a summary of the identity profile for context injection."""
        if not self.profile:
            return {}
        
        return {
            "values": self.profile.values[:5],
            "beliefs": self.profile.beliefs[:5],
            "goals": self.profile.goals[:5],
            "fears": self.profile.fears[:3],
            "strengths": self.profile.strengths[:5],
            "weaknesses": self.profile.weaknesses[:3],
            "motivation_style": self.profile.motivation_style.value,
            "discipline_pattern": self.profile.discipline_pattern.value,
            "energy_pattern": self.profile.energy_pattern.value,
            "learning_style": self.profile.learning_style.value,
            "communication_preference": self.profile.communication_preference.value,
            "coaching_preference": self.profile.coaching_preference.value,
            "confidence_scores": self.profile.confidence_scores,
            "version": self.profile.version,
            "self_image_themes": self._get_recent_self_image_themes(),
        }
    
    def _get_recent_self_image_themes(self) -> List[str]:
        """Get themes from recent self-image snapshots."""
        if not self.profile or not self.profile.self_image_trajectory:
            return []
        recent = self.profile.self_image_trajectory[-5:]
        all_themes = []
        for snap in recent:
            all_themes.extend(snap.get("key_themes", []))
        # Count frequency
        from collections import Counter
        theme_counts = Counter(all_themes)
        return [t for t, _ in theme_counts.most_common(5)]
    
    def get_context_for_prompt(self) -> str:
        """Get formatted identity context for LLM prompts."""
        summary = self.get_profile_summary()
        if not summary:
            return ""
        
        parts = []
        if summary.get("values"):
            parts.append(f"VALUES: {', '.join(summary['values'])}")
        if summary.get("goals"):
            parts.append(f"GOALS: {', '.join(summary['goals'])}")
        if summary.get("motivation_style") != "unknown":
            parts.append(f"MOTIVATION: {summary['motivation_style']}")
        if summary.get("discipline_pattern") != "unknown":
            parts.append(f"DISCIPLINE: {summary['discipline_pattern']}")
        if summary.get("coaching_preference") != "unknown":
            parts.append(f"COACHING STYLE: {summary['coaching_preference']}")
        
        return "\n".join(parts)
    
    def infer_evidence_from_conversation(self, user_message: str, session_data: Dict[str, Any]) -> List[IdentityEvidence]:
        """
        Extract identity evidence from user conversation.
        Returns a list of IdentityEvidence objects for various identity categories.
        """
        evidence_list = []
        content_lower = user_message.lower()
        
        # Goal-related evidence
        goal_patterns = ["want to", "goal is", "aim to", "hope to", "trying to", "would like to", "plan to"]
        if any(pattern in content_lower for pattern in goal_patterns):
            evidence_list.append(IdentityEvidence(
                user_id=self.user_id,
                category="goals",
                content=user_message,
                confidence=0.7,
                source="conversation",
            ))
        
        # Value-related evidence
        value_patterns = ["value", "important to me", "care about", "believe in", "matter to me", "priority"]
        if any(pattern in content_lower for pattern in value_patterns):
            evidence_list.append(IdentityEvidence(
                user_id=self.user_id,
                category="values",
                content=user_message,
                confidence=0.6,
                source="conversation",
            ))
        
        # Strength/weakness evidence
        strength_patterns = ["good at", "strength", "excel at", "strong in", "skilled at", "great at"]
        if any(pattern in content_lower for pattern in strength_patterns):
            evidence_list.append(IdentityEvidence(
                user_id=self.user_id,
                category="strengths",
                content=user_message,
                confidence=0.6,
                source="conversation",
            ))
        
        weakness_patterns = ["bad at", "weakness", "struggle with", "difficult for me", "not good at", "can't"]
        if any(pattern in content_lower for pattern in weakness_patterns):
            evidence_list.append(IdentityEvidence(
                user_id=self.user_id,
                category="weaknesses",
                content=user_message,
                confidence=0.6,
                source="conversation",
            ))
        
        # Fear evidence
        fear_patterns = ["afraid of", "fear", "worried about", "scared of", "anxious about", "nervous about"]
        if any(pattern in content_lower for pattern in fear_patterns):
            evidence_list.append(IdentityEvidence(
                user_id=self.user_id,
                category="fears",
                content=user_message,
                confidence=0.6,
                source="conversation",
            ))
        
        # Belief evidence
        belief_patterns = ["believe", "think that", "convinced that", "know that", "understand that"]
        if any(pattern in content_lower for pattern in belief_patterns):
            evidence_list.append(IdentityEvidence(
                user_id=self.user_id,
                category="beliefs",
                content=user_message,
                confidence=0.5,
                source="conversation",
            ))
        
        # Motivation style evidence
        if any(w in content_lower for w in ["intrinsic", "internal", "for myself", "personal satisfaction", "enjoy"]):
            evidence_list.append(IdentityEvidence(
                user_id=self.user_id,
                category="motivation_style",
                content=user_message,
                confidence=0.5,
                source="conversation",
            ))
        elif any(w in content_lower for w in ["external", "reward", "recognition", "praise", "money", "bonus"]):
            evidence_list.append(IdentityEvidence(
                user_id=self.user_id,
                category="motivation_style",
                content=user_message,
                confidence=0.5,
                source="conversation",
            ))
        
        # Discipline pattern evidence
        if any(w in content_lower for w in ["consistent", "every day", "regular", "routine", "steady", "daily"]):
            evidence_list.append(IdentityEvidence(
                user_id=self.user_id,
                category="discipline_pattern",
                content=user_message,
                confidence=0.5,
                source="conversation",
            ))
        elif any(w in content_lower for w in ["procrastinat", "put off", "delay", "later", "tomorrow", "avoid"]):
            evidence_list.append(IdentityEvidence(
                user_id=self.user_id,
                category="discipline_pattern",
                content=user_message,
                confidence=0.5,
                source="conversation",
            ))
        
        # Energy pattern evidence
        if any(w in content_lower for w in ["morning", "early", "dawn", "am person", "wake up early"]):
            evidence_list.append(IdentityEvidence(
                user_id=self.user_id,
                category="energy_pattern",
                content=user_message,
                confidence=0.5,
                source="conversation",
            ))
        elif any(w in content_lower for w in ["evening", "night", "late", "pm person", "night owl"]):
            evidence_list.append(IdentityEvidence(
                user_id=self.user_id,
                category="energy_pattern",
                content=user_message,
                confidence=0.5,
                source="conversation",
            ))
        
        return evidence_list


# Global instance
identity_model = IdentityModel()
