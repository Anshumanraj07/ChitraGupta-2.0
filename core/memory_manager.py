"""
Memory Manager Module for ChitraGupta 2.0
Handles rolling summaries, 30-day compaction, and session-based memory management.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import hashlib


@dataclass
class SessionSummary:
    """Summary of a conversation session (typically one day)."""
    session_id: str
    user_id: str
    date: str  # YYYY-MM-DD format
    summary: str
    key_topics: List[str]
    dominant_emotion: str
    task_count: int
    created_at: str  # ISO timestamp
    

@dataclass
class CompactedMemory:
    """Compressed memory summary for long-term storage (30+ days)."""
    period_start: str  # YYYY-MM-DD
    period_end: str    # YYYY-MM-DD
    user_id: str
    themes: List[str]
    emotional_trend: str
    key_insights: List[str]
    created_at: str


class MemoryManager:
    def __init__(self, user_id: str = "default_user"):
        self.user_id = user_id
        self.sessions_dir = os.path.join("memory", "sessions", user_id)
        self.compacted_dir = os.path.join("memory", "compacted", user_id)
        self._ensure_directories()
        
    def _ensure_directories(self):
        """Create necessary directories for memory storage."""
        os.makedirs(self.sessions_dir, exist_ok=True)
        os.makedirs(self.compacted_dir, exist_ok=True)
        
    def create_session_summary(self, 
                              conversation_history: List[Dict],
                              dominant_emotion: str = "neutral",
                              key_topics: List[str] = None,
                              task_count: int = 0) -> SessionSummary:
        """
        Create a session summary from conversation history.
        Called at end of day or session boundary.
        """
        if key_topics is None:
            key_topics = []
            
        # Generate session ID based on date and user
        today = datetime.now().date()
        session_id = f"{self.user_id}_{today.isoformat()}"
        
        # Create summary from conversation (simplified - in real implementation 
        # this would use more sophisticated summarization)
        summary = self._create_conversation_summary(conversation_history)
        
        session_summary = SessionSummary(
            session_id=session_id,
            user_id=self.user_id,
            date=today.isoformat(),
            summary=summary,
            key_topics=key_topics,
            dominant_emotion=dominant_emotion,
            task_count=task_count,
            created_at=datetime.now().isoformat()
        )
        
        # Save session summary
        self._save_session_summary(session_summary)
        
        # Check if we need to compact old sessions (older than 30 days)
        self._check_and_compact_old_sessions()
        
        return session_summary
    
    def _create_conversation_summary(self, conversation_history: List[Dict]) -> str:
        """
        Create a concise summary of conversation history.
        In a full implementation, this would use an LLM or more sophisticated NLP.
        For now, we'll use a simple heuristic approach.
        """
        if not conversation_history:
            return "No conversation recorded."
            
        # Extract user messages
        user_messages = [msg.get("content", "") for msg in conversation_history 
                        if msg.get("role") == "user"]
        
        if not user_messages:
            return "No user messages recorded."
            
        # Simple summary: concatenate first few and last few messages
        # In practice, you'd want to use the existing summarization pipeline
        if len(user_messages) <= 3:
            return " ".join(user_messages)
        else:
            beginning = " ".join(user_messages[:2])
            end = " ".join(user_messages[-2:])
            return f"{beginning} ... {end}"
    
    def _save_session_summary(self, session_summary: SessionSummary):
        """Save session summary to disk."""
        filename = f"{session_summary.session_id}.json"
        filepath = os.path.join(self.sessions_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(asdict(session_summary), f, indent=2)
            
    def get_session_summary(self, date_str: str) -> Optional[SessionSummary]:
        """Retrieve session summary for a specific date."""
        filename = f"{self.user_id}_{date_str}.json"
        filepath = os.path.join(self.sessions_dir, filename)
        
        if not os.path.exists(filepath):
            return None
            
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                return SessionSummary(**data)
        except Exception:
            return None
            
    def get_recent_sessions(self, days: int = 14) -> List[SessionSummary]:
        """Get session summaries for the last N days."""
        sessions = []
        today = datetime.now().date()
        
        for i in range(days):
            date = today - timedelta(days=i)
            date_str = date.isoformat()
            session = self.get_session_summary(date_str)
            if session:
                sessions.append(session)
                
        # Sort by date descending (most recent first)
        sessions.sort(key=lambda s: s.date, reverse=True)
        return sessions
    
    def _check_and_compact_old_sessions(self):
        """Check for sessions older than 30 days and compact them."""
        cutoff_date = datetime.now().date() - timedelta(days=30)
        
        # Find session files older than cutoff
        for filename in os.listdir(self.sessions_dir):
            if not filename.endswith('.json'):
                continue
                
            # Extract date from filename: user_YYYY-MM-DD.json
            try:
                date_str = filename.split('_')[1].replace('.json', '')
                file_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                if file_date < cutoff_date:
                    # This session is old enough to be considered for compaction
                    filepath = os.path.join(self.sessions_dir, filename)
                    session_summary = self._load_session_summary(filepath)
                    
                    if session_summary:
                        # Add to batch for compaction (in real implementation, 
                        # we'd batch multiple sessions together)
                        self._compact_session(session_summary)
                        
                        # Remove original session file after successful compaction
                        os.remove(filepath)
                        
            except (IndexError, ValueError):
                # Skip files that don't match expected pattern
                continue
    
    def _load_session_summary(self, filepath: str) -> Optional[SessionSummary]:
        """Load session summary from file."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                return SessionSummary(**data)
        except Exception:
            return None
            
    def _compact_session(self, session: SessionSummary):
        """Create or update compacted memory for old sessions."""
        # For simplicity, we'll create individual compacted files
        # In production, you might want to batch multiple sessions together
        
        # Determine which month this session belongs to for compaction grouping
        session_date = datetime.strptime(session.date, '%Y-%m-%d').date()
        month_key = f"{session_date.year}-{session_date.month:02d}"
        
        compaction_filename = f"{self.user_id}_{month_key}_compacted.json"
        compaction_filepath = os.path.join(self.compacted_dir, compaction_filename)
        
        # Load existing compacted data or create new
        if os.path.exists(compaction_filepath):
            with open(compaction_filepath, 'r') as f:
                compacted_data = json.load(f)
            compacted_memory = CompactedMemory(**compacted_data)
        else:
            compacted_memory = CompactedMemory(
                period_start=session.date,  # Will update this properly below
                period_end=session.date,
                user_id=self.user_id,
                themes=[],
                emotional_trend="stable",
                key_insights=[],
                created_at=datetime.now().isoformat()
            )
        
        # Update the compacted memory with this session's data
        # In a real implementation, you'd do proper aggregation here
        compacted_memory.key_insights.append(session.summary[:100] + "...")  # Preview
        if session.key_topics:
            compacted_memory.themes.extend(session.key_topics)
        compacted_memory.period_end = session.date  # Keep extending end date
        
        # Deduplicate and limit
        compacted_memory.themes = list(set(compacted_memory.themes))[:10]
        compacted_memory.key_insights = list(set(compacted_memory.key_insights))[:5]
        
        # Save updated compacted memory
        with open(compaction_filepath, 'w') as f:
            json.dump(asdict(compacted_memory), f, indent=2)
            
    def get_compacted_memories(self, months: int = 6) -> List[CompactedMemory]:
        """Get compacted memories for the last N months."""
        memories = []
        cutoff_date = datetime.now().date() - timedelta(days=months*30)
        
        for filename in os.listdir(self.compacted_dir):
            if not filename.endswith('_compacted.json'):
                continue
                
            try:
                # Extract date from filename: user_YYYY-MM_compacted.json
                parts = filename.split('_')
                year_month = f"{parts[1]}-{parts[2]}"  # YYYY-MM
                year, month = map(int, year_month.split('-'))
                
                # Approximate check - files are organized by month
                file_date = datetime(year, month, 1).date()
                if file_date >= cutoff_date.replace(day=1):
                    filepath = os.path.join(self.compacted_dir, filename)
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        memories.append(CompactedMemory(**data))
            except (IndexError, ValueError):
                continue
                
        # Sort by period_start descending (most recent first)
        memories.sort(key=lambda m: m.period_start, reverse=True)
        return memories
        
    def get_memory_context_for_prompt(self, days: int = 14) -> str:
        """
        Get formatted memory context for injection into prompts.
        Combines recent session summaries and compacts older memories.
        """
        recent_sessions = self.get_recent_sessions(days)
        
        if not recent_sessions:
            return "No prior conversation history available."
            
        context_parts = []
        context_parts.append(f"Recent conversation history (last {len(recent_sessions)} days):")
        
        for session in recent_sessions[:5]:  # Limit to most recent 5 sessions
            context_parts.append(f"- [{session.date}] {session.summary}")
            if session.key_topics:
                context_parts.append(f"  Topics: {', '.join(session.key_topics[:3])}")
            if session.task_count > 0:
                context_parts.append(f"  Tasks discussed: {session.task_count}")
                
        # Add compacted memory if we have older sessions
        if len(recent_sessions) > 5:
            compacted = self.get_compacted_memories(months=2)
            if compacted:
                context_parts.append(f"\nEarlier trends (last {len(compacted)} months):")
                for mem in compacted[:3]:  # Show most recent 3 compacted periods
                    context_parts.append(f"- [{mem.period_start} to {mem.period_end}] {', '.join(mem.key_insights[:2])}")
                    
        return "\n".join(context_parts)


# Global instance for easy access
memory_manager = MemoryManager()