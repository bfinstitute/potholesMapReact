"""
DiskCache — file-based response cache with zero dependencies on MongoDB.

Uses the `diskcache` library backed by SQLite (no password, no server, no login).
Works completely offline. Cache lives in a local directory and is reset with one call.

Benefits over MongoDB cache:
- No credentials needed
- Works without internet
- Sub-millisecond reads (local disk)
- Reset with a single function call or DELETE /cache/reset endpoint

Cache directory: backend/app/.cache/  (auto-created, gitignored)

Usage:
    from disk_cache import get_cached, set_cached, reset_cache, cache_stats
    
    # Get/set
    val = get_cached("my-key")
    set_cached("my-key", {"data": 123}, ttl=3600)
    
    # Reset entire cache
    reset_cache()
    
    # Stats
    print(cache_stats())
"""

import os
import hashlib
from pathlib import Path
from typing import Optional, Any, Dict
from datetime import datetime

try:
    import diskcache
    _DISKCACHE_AVAILABLE = True
except ImportError:
    _DISKCACHE_AVAILABLE = False

# ---------------------------------------------------------------------------
# Cache directory — sits alongside this file, gitignored
# ---------------------------------------------------------------------------
_CACHE_DIR = Path(__file__).parent / ".cache"
_CACHE: Optional[Any] = None  # Lazy-initialized


def _get_cache():
    """Get or create the diskcache Cache instance."""
    global _CACHE
    if not _DISKCACHE_AVAILABLE:
        return None
    if _CACHE is None:
        _CACHE_DIR.mkdir(exist_ok=True)
        _CACHE = diskcache.Cache(str(_CACHE_DIR), size_limit=500 * 1024 * 1024)  # 500MB max
    return _CACHE


def make_cache_key(prefix: str, text: str) -> str:
    """Create a consistent cache key from a prefix + text."""
    h = hashlib.md5(text.strip().lower().encode()).hexdigest()
    return f"{prefix}:{h}"


# ---------------------------------------------------------------------------
# Core cache operations
# ---------------------------------------------------------------------------

def get_cached(key: str) -> Optional[Any]:
    """
    Get a value from the disk cache.
    Returns None on cache miss or if cache is unavailable.
    """
    cache = _get_cache()
    if cache is None:
        return None
    try:
        return cache.get(key)
    except Exception:
        return None


def set_cached(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """
    Store a value in the disk cache.
    
    Args:
        key:   Cache key string
        value: Any JSON-serializable value
        ttl:   Time-to-live in seconds (None = no expiry)
    
    Returns True on success.
    """
    cache = _get_cache()
    if cache is None:
        return False
    try:
        cache.set(key, value, expire=ttl)
        return True
    except Exception:
        return False


def delete_cached(key: str) -> bool:
    """Delete a specific key from the cache."""
    cache = _get_cache()
    if cache is None:
        return False
    try:
        cache.delete(key)
        return True
    except Exception:
        return False


def reset_cache() -> Dict[str, Any]:
    """
    Clear the ENTIRE disk cache. Use this for testing / dev resets.
    No password or login required.
    
    Returns summary of what was cleared.
    """
    global _CACHE
    cache = _get_cache()
    before_count = 0
    before_size = 0

    if cache is not None:
        try:
            before_count = len(cache)
            before_size = cache.volume()
            cache.clear()
            print(f"[DiskCache] Reset: cleared {before_count} entries ({before_size // 1024}KB)")
        except Exception as e:
            print(f"[DiskCache] Reset error: {e}")

    return {
        "cleared": True,
        "entries_cleared": before_count,
        "bytes_freed": before_size,
        "cache_dir": str(_CACHE_DIR),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def cache_stats() -> Dict[str, Any]:
    """Return stats about the current cache state."""
    cache = _get_cache()
    if cache is None:
        return {
            "available": False,
            "reason": "diskcache not installed (pip install diskcache)",
        }
    try:
        return {
            "available": True,
            "cache_dir": str(_CACHE_DIR),
            "entry_count": len(cache),
            "size_bytes": cache.volume(),
            "size_mb": round(cache.volume() / 1024 / 1024, 2),
            "size_limit_mb": 500,
        }
    except Exception as e:
        return {"available": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Convenience wrappers for common patterns
# ---------------------------------------------------------------------------

# Default TTLs (seconds)
TTL_CHAT_RESPONSE = 24 * 3600           # 24 hours — chat responses
TTL_API_DATA = 7 * 24 * 3600            # 7 days — external API data (CDC, Census)
TTL_SUMMARY = 30 * 24 * 3600           # 30 days — static summaries
TTL_NONE = None                          # No expiry


def get_chat_response(question: str) -> Optional[Dict]:
    """Get a cached chat response for a question."""
    key = make_cache_key("chat", question)
    return get_cached(key)


def set_chat_response(question: str, response: Dict, ttl: int = TTL_CHAT_RESPONSE) -> bool:
    """Cache a chat response."""
    key = make_cache_key("chat", question)
    return set_cached(key, response, ttl=ttl)


def get_api_data(api_name: str, params: str = "") -> Optional[Any]:
    """Get cached API data (CDC PLACES, Census, etc.)."""
    key = make_cache_key(f"api:{api_name}", params)
    return get_cached(key)


def set_api_data(api_name: str, data: Any, params: str = "", ttl: int = TTL_API_DATA) -> bool:
    """Cache API data."""
    key = make_cache_key(f"api:{api_name}", params)
    return set_cached(key, data, ttl=ttl)
