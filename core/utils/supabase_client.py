"""
ChitraGupta 2.0 — Supabase Client
Shared Supabase client for all modules.
"""

import os
import logging
from typing import Optional
from supabase import create_client, Client

logger = logging.getLogger("chitragupta.supabase_client")

_supabase_client: Optional[Client] = None


def get_supabase_client() -> Optional[Client]:
    """Get or create Supabase client singleton."""
    global _supabase_client
    
    if _supabase_client is not None:
        return _supabase_client
    
    # Try to get credentials from environment
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
    
    if not url or not key:
        logger.warning("Supabase credentials not found in environment. Set SUPABASE_URL and SUPABASE_ANON_KEY")
        return None
    
    try:
        _supabase_client = create_client(url, key)
        logger.info("Supabase client initialized")
        return _supabase_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None


def reset_supabase_client():
    """Reset the singleton (useful for testing)."""
    global _supabase_client
    _supabase_client = None


# For backward compatibility
supabase = get_supabase_client()