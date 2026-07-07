"""
ChitraGupta 2.0 — Adaptive Memory
Smart memory recall prioritizing coaching effectiveness.
"""

import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from core.schemas.memory import (
    MemoryEntry, MemoryType, MemoryPriority, MemoryQuery, MemoryRetrievalResult,
    MemoryConsolidationRule, DEFAULT_CONSOLIDATION_RULES
)
from core.utils.supabase_client import get_supabase_client

logger = logging.getLogger("chitragupta.adaptive_memory")


class AdaptiveMemory:
    """
    Adaptive memory system that prioritizes recall based on coaching relevance.
    Retrieves only what helps the next decision - no irrelevant history dumps.
    """
    
    def __init__(self, user_id: str = "default_user"):
        self.user_id = user_id
        self._memory_cache: List[MemoryEntry] = []
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=5)
    
    def add_memory(self, entry: MemoryEntry):
        """Add a new memory entry."""
        entry.id = entry.id or str(uuid.uuid4())[:8]
        entry.user_id = self.user_id
        
        try:
            supabase = get_supabase_client()
            if supabase:
                data = entry.model_dump()
                data["timestamp"] = entry.timestamp.isoformat()
                if entry.last_accessed:
                    data["last_accessed"] = entry.last_accessed.isoformat()
                
                supabase.table("adaptive_memories").insert(data).execute()
                logger.debug(f"Added memory: {entry.memory_type.value} - {entry.summary[:50]}")
        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
        
        # Invalidate cache
        self._cache_timestamp = None
    
    def add_memories_batch(self, entries: List[MemoryEntry]):
        """Add multiple memories at once."""
        for entry in entries:
            self.add_memory(entry)
    
    def retrieve(self, query: MemoryQuery) -> MemoryRetrievalResult:
        """Retrieve memories relevant to the current context."""
        # Load memories if cache expired
        self._ensure_cache_loaded()
        
        # Filter and score memories
        scored_memories = []
        
        for memory in self._memory_cache:
            # Apply filters
            if query.include_types and memory.memory_type not in query.include_types:
                continue
            if query.exclude_types and memory.memory_type in query.exclude_types:
                continue
            if query.time_window_days:
                cutoff = datetime.utcnow() - timedelta(days=query.time_window_days)
                if memory.timestamp < cutoff:
                    continue
            
            # Calculate relevance
            relevance = self._calculate_relevance(memory, query)
            
            if relevance >= query.min_relevance:
                scored_memories.append((memory, relevance))
        
        # Sort by relevance (highest first)
        scored_memories.sort(key=lambda x: x[1], reverse=True)
        
        # Take top N
        selected = [m for m, _ in scored_memories[:query.max_entries]]
        
        # Update access metadata
        for memory in selected:
            memory.access_count += 1
            memory.last_accessed = datetime.utcnow()
            memory.retrieval_contexts.append(query.current_context[:100])
            self._update_memory_access(memory)
        
        # Coverage stats
        coverage = defaultdict(int)
        for memory in selected:
            coverage[memory.memory_type.value] += 1
        
        return MemoryRetrievalResult(
            entries=selected,
            total_available=len(self._memory_cache),
            retrieval_strategy="adaptive_relevance",
            coverage=dict(coverage)
        )
    
    def _ensure_cache_loaded(self):
        """Load memories from Supabase if cache expired."""
        if (self._cache_timestamp and 
            datetime.utcnow() - self._cache_timestamp < self._cache_ttl and
            self._memory_cache):
            return
        
        try:
            supabase = get_supabase_client()
            if supabase:
                response = supabase.table("adaptive_memories").select("*").eq("user_id", self.user_id).order("timestamp", desc=True).limit(500).execute()
                
                self._memory_cache = []
                for row in response.data:
                    # Convert datetime strings
                    row["timestamp"] = datetime.fromisoformat(row["timestamp"])
                    if row.get("last_accessed"):
                        row["last_accessed"] = datetime.fromisoformat(row["last_accessed"])
                    
                    # Convert enums
                    row["memory_type"] = MemoryType(row["memory_type"])
                    row["priority"] = MemoryPriority(row["priority"])
                    
                    self._memory_cache.append(MemoryEntry(**row))
                
                self._cache_timestamp = datetime.utcnow()
                logger.debug(f"Loaded {len(self._memory_cache)} memories for {self.user_id}")
        except Exception as e:
            logger.error(f"Failed to load memories: {e}")
            self._memory_cache = []
            self._cache_timestamp = datetime.utcnow()
    
    def _calculate_relevance(self, memory: MemoryEntry, query: MemoryQuery) -> float:
        """Calculate relevance score for a memory given the query.

        Priority weighting (P6):
          - Recency: recent memories surface faster (exponential decay)
          - Importance: goal/habit/identity memories get stronger boosts
          - Goal-related: explicit related_goal or goal-keyword match
          - Habit-related: habit/routine memory type
          - Identity-related: identity/behavioral-pattern memories
        Also penalises low-value conversational noise so it does not clog the
        top of the retrieval window.
        """
        score = memory.relevance_score * 0.3  # Base relevance

        # Recency boost (exponential decay — last 20 days matter most)
        days_old = (datetime.utcnow() - memory.timestamp).days
        recency_boost = max(0, 1 - days_old * 0.05) * 0.2
        score += recency_boost

        # Priority boost
        priority_weights = {
            MemoryPriority.CRITICAL: 0.3,
            MemoryPriority.HIGH: 0.2,
            MemoryPriority.MEDIUM: 0.1,
            MemoryPriority.LOW: 0.0,
            MemoryPriority.ARCHIVAL: -0.1,
        }
        score += priority_weights.get(memory.priority, 0)

        # Coaching effectiveness boost
        score += memory.coaching_effectiveness * 0.15

        # Importance boost — goal / habit / identity memories are intrinsically valuable
        important_types = {
            MemoryType.GOAL: 0.15,
            MemoryType.IDENTITY: 0.15,
            MemoryType.PATTERN: 0.1,
            MemoryType.STRUGGLE: 0.08,
            MemoryType.INSIGHT: 0.1,
            MemoryType.INTERVENTION: 0.08,
        }
        score += important_types.get(memory.memory_type, 0.0)

        # Goal-related boost — strongly prefer memories tied to the active goal
        if query.goal:
            goal_lower = query.goal.lower()
            if memory.related_goal and memory.related_goal.lower() == goal_lower:
                score += 0.2
            elif goal_lower in memory.content.lower():
                score += 0.12

        # Struggle match
        if query.struggle and query.struggle.lower() in memory.content.lower():
            score += 0.1

        # Habit-related boost — habits/routines should surface for action contexts
        if memory.memory_type in (getattr(MemoryType, "HABIT", None), getattr(MemoryType, "ROUTINE", None)) or "habit" in memory.content.lower() or "routine" in memory.content.lower():
            if query.current_context and any(
                k in query.current_context.lower() for k in ("habit", "routine", "daily", "consistency", "streak", "missed")
            ):
                score += 0.15

        # Identity-related boost — identity memories surface for reflection contexts
        if memory.memory_type == MemoryType.IDENTITY:
            if query.current_context and any(
                k in query.current_context.lower() for k in ("who", "i am", "identity", "values", "believe", "always", "never", "struggle")
            ):
                score += 0.15

        # Penalise low-value conversational noise (avoid irrelevant history dumps)
        if memory.memory_type == MemoryType.CONVERSATION and memory.coaching_effectiveness < 0.3:
            score -= 0.1

        # Context match
        context_match = self._match_context(memory, query)
        score += context_match * 0.25

        # Behavioral pattern match
        if query.behavioral_patterns:
            pattern_match = len(set(memory.behavioral_patterns) & set(query.behavioral_patterns)) / max(len(query.behavioral_patterns), 1)
            score += pattern_match * 0.1

        # Coaching strategy match
        if query.coaching_strategy and query.coaching_strategy in memory.retrieval_contexts:
            score += 0.1

        # Active task match
        if query.active_task and query.active_task in memory.content:
            score += 0.15

        # Access frequency (popular memories more relevant, capped)
        access_boost = min(memory.access_count * 0.01, 0.1)
        score += access_boost

        return max(0, min(1, score))
    
    def _match_context(self, memory: MemoryEntry, query: MemoryQuery) -> float:
        """Match memory context to query context."""
        score = 0.0
        
        # Type relevance to current context
        type_relevance = {
            "decision": [MemoryType.INTERVENTION, MemoryType.PATTERN, MemoryType.INSIGHT],
            "planning": [MemoryType.PATTERN, MemoryType.GOAL, MemoryType.INTERVENTION],
            "execution": [MemoryType.TASK_OUTCOME, MemoryType.SUCCESS, MemoryType.FAILURE, MemoryType.INTERVENTION],
            "reflection": [MemoryType.INSIGHT, MemoryType.IDENTITY, MemoryType.PATTERN],
            "struggle": [MemoryType.STRUGGLE, MemoryType.FAILURE, MemoryType.INTERVENTION, MemoryType.PATTERN],
            "progress": [MemoryType.SUCCESS, MemoryType.TASK_OUTCOME, MemoryType.PATTERN],
        }
        
        current = query.current_context.lower()
        for ctx_type, relevant_types in type_relevance.items():
            if ctx_type in current and memory.memory_type in relevant_types:
                score += 0.3
                break
        
        return min(score, 1.0)
    
    def _update_memory_access(self, memory: MemoryEntry):
        """Update memory access metadata in Supabase."""
        try:
            supabase = get_supabase_client()
            if supabase:
                supabase.table("adaptive_memories").update({
                    "access_count": memory.access_count,
                    "last_accessed": memory.last_accessed.isoformat() if memory.last_accessed else None,
                    "retrieval_contexts": memory.retrieval_contexts[-10:],  # Keep last 10
                }).eq("id", memory.id).execute()
        except Exception as e:
            logger.warning(f"Failed to update memory access: {e}")
    
    def consolidate(self) -> Dict[str, int]:
        """Run memory consolidation rules (30-day compaction)."""
        results = {"consolidated": 0, "archived": 0}
        
        try:
            supabase = get_supabase_client()
            if not supabase:
                return results
            
            # Get memories older than 30 days
            cutoff = datetime.utcnow() - timedelta(days=30)
            response = supabase.table("adaptive_memories").select("*").eq("user_id", self.user_id).lt("timestamp", cutoff.isoformat()).execute()
            
            old_memories = []
            for row in response.data:
                row["timestamp"] = datetime.fromisoformat(row["timestamp"])
                if row.get("last_accessed"):
                    row["last_accessed"] = datetime.fromisoformat(row["last_accessed"])
                row["memory_type"] = MemoryType(row["memory_type"])
                row["priority"] = MemoryPriority(row["priority"])
                old_memories.append(MemoryEntry(**row))
            
            if not old_memories:
                return results
            
            # Apply consolidation rules
            for rule in DEFAULT_CONSOLIDATION_RULES:
                consolidated = self._apply_consolidation_rule(old_memories, rule)
                results["consolidated"] += consolidated
            
            # Archive remaining old memories
            for memory in old_memories:
                if memory.priority != MemoryPriority.ARCHIVAL:
                    memory.priority = MemoryPriority.ARCHIVAL
                    self._update_memory_priority(memory)
                    results["archived"] += 1
            
            # Invalidate cache
            self._cache_timestamp = None
            
            logger.info(f"Consolidation complete: {results}")
            
        except Exception as e:
            logger.error(f"Consolidation failed: {e}")
        
        return results
    
    def _apply_consolidation_rule(self, memories: List[MemoryEntry], rule: MemoryConsolidationRule) -> int:
        """Apply a single consolidation rule."""
        # Filter source memories
        source_memories = [m for m in memories if m.memory_type in rule.source_types]
        
        if len(source_memories) < 3:  # Need minimum group
            return 0
        
        # Group by theme/goal
        groups = defaultdict(list)
        for mem in source_memories:
            key = mem.related_goal or "general"
            groups[key].append(mem)
        
        consolidated_count = 0
        
        for goal, group_memories in groups.items():
            if len(group_memories) < 3:
                continue
            
            # Check condition (simplified)
            if rule.consolidation_fn == "consolidate_recurring_insights":
                consolidated = self._consolidate_insights(group_memories, rule.target_type, goal)
            elif rule.consolidation_fn == "consolidate_task_interventions":
                consolidated = self._consolidate_interventions(group_memories, rule.target_type, goal)
            elif rule.consolidation_fn == "consolidate_identity_patterns":
                consolidated = self._consolidate_identity(group_memories, rule.target_type, goal)
            else:
                continue
            
            consolidated_count += consolidated
        
        return consolidated_count
    
    def _consolidate_insights(self, memories: List[MemoryEntry], target_type: MemoryType, goal: str) -> int:
        """Consolidate recurring insights into patterns."""
        # Find common themes
        all_content = " ".join(m.content for m in memories)
        
        # Create consolidated pattern memory
        pattern_memory = MemoryEntry(
            id=str(uuid.uuid4())[:8],
            user_id=self.user_id,
            memory_type=target_type,
            priority=MemoryPriority.HIGH,
            content=f"Recurring insight pattern for {goal}: {self._extract_common_theme(all_content)}",
            summary=f"Pattern: {goal} - {self._extract_common_theme(all_content)[:50]}",
            timestamp=datetime.utcnow(),
            related_goal=goal,
            coaching_effectiveness=sum(m.coaching_effectiveness for m in memories) / len(memories),
            behavioral_patterns=list(set(p for m in memories for p in m.behavioral_patterns)),
            relevance_score=0.8,
        )
        
        self.add_memory(pattern_memory)
        
        # Mark source as archived
        for m in memories:
            m.priority = MemoryPriority.ARCHIVAL
            self._update_memory_priority(m)
        
        return 1
    
    def _consolidate_interventions(self, memories: List[MemoryEntry], target_type: MemoryType, goal: str) -> int:
        """Consolidate task outcomes into intervention knowledge."""
        # Separate successes and failures
        successes = [m for m in memories if m.memory_type == MemoryType.SUCCESS]
        failures = [m for m in memories if m.memory_type == MemoryType.FAILURE]
        outcomes = [m for m in memories if m.memory_type == MemoryType.TASK_OUTCOME]
        
        if not (successes or failures or outcomes):
            return 0
        
        # Determine what worked
        worked = [m.content for m in successes if m.coaching_effectiveness > 0.5]
        didnt_work = [m.content for m in failures if m.coaching_effectiveness > 0.5]
        
        intervention_memory = MemoryEntry(
            id=str(uuid.uuid4())[:8],
            user_id=self.user_id,
            memory_type=target_type,
            priority=MemoryPriority.HIGH,
            content=f"Intervention knowledge for {goal}: Worked - {'; '.join(worked[:2])}. Didn't work - {'; '.join(didnt_work[:2])}",
            summary=f"Intervention: {goal} - {len(worked)} effective, {len(didnt_work)} ineffective",
            timestamp=datetime.utcnow(),
            related_goal=goal,
            coaching_effectiveness=sum(m.coaching_effectiveness for m in memories) / len(memories),
            intervention_type="task_coaching",
            relevance_score=0.85,
        )
        
        self.add_memory(intervention_memory)
        
        for m in memories:
            m.priority = MemoryPriority.ARCHIVAL
            self._update_memory_priority(m)
        
        return 1
    
    def _consolidate_identity(self, memories: List[MemoryEntry], target_type: MemoryType, goal: str) -> int:
        """Consolidate identity-related memories into stable patterns."""
        identity_memories = [m for m in memories if m.memory_type == MemoryType.IDENTITY]
        goal_memories = [m for m in memories if m.memory_type == MemoryType.GOAL]
        struggle_memories = [m for m in memories if m.memory_type == MemoryType.STRUGGLE]
        
        if not (identity_memories or goal_memories or struggle_memories):
            return 0
        
        # Extract stable identity themes
        themes = self._extract_identity_themes(identity_memories + goal_memories + struggle_memories)
        
        pattern_memory = MemoryEntry(
            id=str(uuid.uuid4())[:8],
            user_id=self.user_id,
            memory_type=target_type,
            priority=MemoryPriority.HIGH,
            content=f"Stable identity pattern for {goal}: {'; '.join(themes)}",
            summary=f"Identity pattern: {goal} - {themes[0] if themes else 'emerging'}",
            timestamp=datetime.utcnow(),
            related_goal=goal,
            behavioral_patterns=themes,
            relevance_score=0.75,
        )
        
        self.add_memory(pattern_memory)
        
        for m in memories:
            m.priority = MemoryPriority.ARCHIVAL
            self._update_memory_priority(m)
        
        return 1
    
    def _extract_common_theme(self, text: str) -> str:
        """Extract common theme from text."""
        # Simple keyword extraction
        themes = []
        text_lower = text.lower()
        theme_keywords = {
            "procrastination": ["procrastinat", "delay", "put off", "later"],
            "perfectionism": ["perfect", "exact", "right", "flawless"],
            "overwhelm": ["overwhelm", "too much", "can't handle", "stress"],
            "motivation": ["motivat", "drive", "want", "desire"],
            "fear": ["fear", "afraid", "scared", "anxious"],
            "habit": ["habit", "routine", "daily", "consistent"],
            "energy": ["energy", "tired", "exhausted", "drained"],
            "focus": ["focus", "concentrate", "distract", "attention"],
        }
        
        for theme, keywords in theme_keywords.items():
            if any(kw in text_lower for kw in keywords):
                themes.append(theme)
        
        return themes[0] if themes else "general"
    
    def _extract_identity_themes(self, memories: List[MemoryEntry]) -> List[str]:
        """Extract identity themes from memories."""
        all_content = " ".join(m.content for m in memories)
        
        themes = []
        content_lower = all_content.lower()
        identity_themes = {
            "growth_oriented": ["grow", "improve", "develop", "learn", "better"],
            "disciplined": ["discipline", "consistent", "routine", "habit", "control"],
            "health_focused": ["health", "fit", "exercise", "strong", "energy"],
            "career_driven": ["career", "work", "job", "professional", "success"],
            "relationship_oriented": ["relationship", "family", "friend", "connect", "love"],
            "creative": ["creative", "create", "art", "write", "make", "build"],
            "mindful": ["mindful", "present", "aware", "peace", "calm", "balance"],
            "achievement_oriented": ["achieve", "accomplish", "goal", "reach", "complete"],
        }
        
        for theme, keywords in identity_themes.items():
            if any(kw in content_lower for kw in keywords):
                themes.append(theme)
        
        return themes[:5]
    
    def _update_memory_priority(self, memory: MemoryEntry):
        """Update memory priority in Supabase."""
        try:
            supabase = get_supabase_client()
            if supabase:
                supabase.table("adaptive_memories").update({
                    "priority": memory.priority.value,
                }).eq("id", memory.id).execute()
        except Exception as e:
            logger.warning(f"Failed to update memory priority: {e}")
    
    def get_context_for_prompt(self, query: MemoryQuery, max_chars: int = 1000) -> str:
        """Get formatted memory context for LLM prompts."""
        result = self.retrieve(query)
        
        if not result.entries:
            return ""
        
        parts = ["RELEVANT MEMORY:"]
        char_count = 0
        
        for entry in result.entries:
            if char_count >= max_chars:
                break
            
            line = f"- [{entry.memory_type.value}] {entry.summary}"
            if char_count + len(line) > max_chars:
                break
            
            parts.append(line)
            char_count += len(line)
        
        return "\n".join(parts)
    
    def record_conversation(self, content: str, summary: str, session_id: str, 
                          coaching_effectiveness: float = 0.5, user_response: str = "neutral",
                          intervention_type: Optional[str] = None):
        """Record a conversation memory."""
        entry = MemoryEntry(
            id=str(uuid.uuid4())[:8],
            user_id=self.user_id,
            memory_type=MemoryType.CONVERSATION,
            priority=MemoryPriority.MEDIUM,
            content=content,
            summary=summary,
            timestamp=datetime.utcnow(),
            session_id=session_id,
            coaching_effectiveness=coaching_effectiveness,
            user_response=user_response,
            intervention_type=intervention_type,
            relevance_score=0.7,
        )
        self.add_memory(entry)
    
    def record_task_outcome(self, task_id: str, outcome: str, success: bool, 
                          coaching_effectiveness: float = 0.5, task_type: str = "micro"):
        """Record a task outcome memory."""
        entry = MemoryEntry(
            id=str(uuid.uuid4())[:8],
            user_id=self.user_id,
            memory_type=MemoryType.SUCCESS if success else MemoryType.FAILURE,
            priority=MemoryPriority.HIGH if success else MemoryPriority.MEDIUM,
            content=f"Task {task_id}: {outcome}",
            summary=f"{'Completed' if success else 'Failed'}: {task_id} ({task_type})",
            timestamp=datetime.utcnow(),
            related_task_id=task_id,
            coaching_effectiveness=coaching_effectiveness,
            user_response="positive" if success else "negative",
            intervention_type="task_coaching",
            relevance_score=0.8,
        )
        self.add_memory(entry)
    
    def record_insight(self, insight: str, session_id: str, goal: Optional[str] = None,
                      coaching_effectiveness: float = 0.6):
        """Record an insight memory."""
        entry = MemoryEntry(
            id=str(uuid.uuid4())[:8],
            user_id=self.user_id,
            memory_type=MemoryType.INSIGHT,
            priority=MemoryPriority.HIGH,
            content=insight,
            summary=f"Insight: {insight[:80]}",
            timestamp=datetime.utcnow(),
            session_id=session_id,
            related_goal=goal,
            coaching_effectiveness=coaching_effectiveness,
            relevance_score=0.75,
        )
        self.add_memory(entry)


# Global instance
adaptive_memory = AdaptiveMemory()