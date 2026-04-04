"""
MongoDB client for SAAF chatbot analytics and caching.

Provides collections for:
- Query tracking and analytics
- Response caching
- Groq API monitoring
- Data source freshness tracking
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database
import hashlib


class MongoDBClient:
    """MongoDB client with lazy connection for SAAF chatbot."""

    def __init__(self):
        self._client: Optional[MongoClient] = None
        self._db: Optional[Database] = None
        self._enabled = False

    def connect(self) -> bool:
        """Establish MongoDB connection if MONGODB_URI is configured."""
        if self._client is not None:
            return True  # Already connected

        mongodb_uri = os.getenv("MONGODB_URI")
        if not mongodb_uri:
            print("[MongoDB] MONGODB_URI not configured, skipping MongoDB features")
            return False

        try:
            self._client = MongoClient(
                mongodb_uri,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                connectTimeoutMS=5000,
            )
            # Test connection
            self._client.server_info()

            db_name = os.getenv("MONGODB_DB_NAME", "saaf_chatbot")
            self._db = self._client[db_name]
            self._enabled = True

            # Create indexes
            self._create_indexes()

            print(f"[MongoDB] Connected successfully to database: {db_name}")
            return True
        except Exception as e:
            print(f"[MongoDB] Connection failed: {e}")
            self._enabled = False
            return False

    def _create_indexes(self):
        """Create indexes for better query performance."""
        if not self._db:
            return

        try:
            # Query tracking indexes
            self._db.queries.create_index([("timestamp", DESCENDING)])
            self._db.queries.create_index([("question_hash", ASCENDING)])
            self._db.queries.create_index([("intent_detected", ASCENDING)])

            # Response cache indexes
            self._db.response_cache.create_index([("question_hash", ASCENDING)])
            self._db.response_cache.create_index([("created_at", DESCENDING)])
            # TTL index - auto-delete cached responses after 7 days
            self._db.response_cache.create_index(
                [("created_at", ASCENDING)],
                expireAfterSeconds=7 * 24 * 60 * 60  # 7 days
            )

            # Groq monitoring indexes
            self._db.groq_responses.create_index([("created_at", DESCENDING)])
            self._db.groq_responses.create_index([("question_hash", ASCENDING)])

            print("[MongoDB] Indexes created successfully")
        except Exception as e:
            print(f"[MongoDB] Index creation warning: {e}")

    @property
    def enabled(self) -> bool:
        """Check if MongoDB is enabled and connected."""
        return self._enabled

    @property
    def queries(self) -> Optional[Collection]:
        """Get queries collection for tracking all chat queries."""
        return self._db.queries if self._db else None

    @property
    def response_cache(self) -> Optional[Collection]:
        """Get response cache collection."""
        return self._db.response_cache if self._db else None

    @property
    def groq_responses(self) -> Optional[Collection]:
        """Get Groq API response monitoring collection."""
        return self._db.groq_responses if self._db else None

    @property
    def data_sources(self) -> Optional[Collection]:
        """Get data source freshness tracking collection."""
        return self._db.data_sources if self._db else None

    def close(self):
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            self._enabled = False
            print("[MongoDB] Connection closed")


# Global MongoDB client instance
_mongo_client = MongoDBClient()


def get_mongo_client() -> MongoDBClient:
    """Get the global MongoDB client instance."""
    if not _mongo_client.enabled:
        _mongo_client.connect()
    return _mongo_client


def hash_question(question: str) -> str:
    """Create a consistent hash for a question."""
    return hashlib.md5(question.strip().lower().encode()).hexdigest()


def log_query(
    question: str,
    intent_detected: Optional[str] = None,
    data_sources_used: Optional[List[str]] = None,
    response_time_ms: Optional[int] = None,
    groq_called: bool = False,
    user_ip_hash: Optional[str] = None,
) -> bool:
    """Log a query to MongoDB for analytics."""
    client = get_mongo_client()
    if not client.enabled or not client.queries:
        return False

    try:
        doc = {
            "question": question,
            "question_hash": hash_question(question),
            "intent_detected": intent_detected,
            "data_sources_used": data_sources_used or [],
            "response_time_ms": response_time_ms,
            "groq_api_called": groq_called,
            "user_ip_hash": user_ip_hash,
            "timestamp": datetime.utcnow(),
        }
        client.queries.insert_one(doc)
        return True
    except Exception as e:
        print(f"[MongoDB] Failed to log query: {e}")
        return False


def get_cached_response(question: str, context_signature: str) -> Optional[Dict[str, Any]]:
    """Get a cached response if available."""
    client = get_mongo_client()
    if not client.enabled or not client.response_cache:
        return None

    try:
        q_hash = hash_question(question)
        cached = client.response_cache.find_one({
            "question_hash": q_hash,
            "context_signature": context_signature,
        })
        if cached and cached.get("response"):
            print(f"[MongoDB] Cache hit for question: {question[:50]}...")
            return {
                "response": cached["response"],
                "highlight_data": cached.get("highlight_data"),
                "cached_at": cached.get("created_at"),
            }
        return None
    except Exception as e:
        print(f"[MongoDB] Failed to get cached response: {e}")
        return None


def cache_response(
    question: str,
    context_signature: str,
    response: str,
    highlight_data: Optional[List[Dict]] = None,
) -> bool:
    """Cache a response for future use."""
    client = get_mongo_client()
    if not client.enabled or not client.response_cache:
        return False

    try:
        doc = {
            "question": question,
            "question_hash": hash_question(question),
            "context_signature": context_signature,
            "response": response,
            "highlight_data": highlight_data,
            "created_at": datetime.utcnow(),
        }
        client.response_cache.update_one(
            {"question_hash": doc["question_hash"], "context_signature": context_signature},
            {"$set": doc},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"[MongoDB] Failed to cache response: {e}")
        return False


def log_groq_response(
    question: str,
    context_provided: Dict[str, str],
    groq_response: str,
    temperature: float,
    seed: int,
    model: str,
    response_time_ms: int,
    tokens_used: Optional[int] = None,
    grounded_correctly: Optional[bool] = None,
) -> bool:
    """Log a Groq API response for quality monitoring."""
    client = get_mongo_client()
    if not client.enabled or not client.groq_responses:
        return False

    try:
        doc = {
            "question": question,
            "question_hash": hash_question(question),
            "context_provided": context_provided,
            "groq_response": groq_response,
            "temperature": temperature,
            "seed": seed,
            "model": model,
            "response_time_ms": response_time_ms,
            "tokens_used": tokens_used,
            "grounded_correctly": grounded_correctly,
            "created_at": datetime.utcnow(),
        }
        client.groq_responses.insert_one(doc)
        return True
    except Exception as e:
        print(f"[MongoDB] Failed to log Groq response: {e}")
        return False


def get_query_analytics(days: int = 7) -> Dict[str, Any]:
    """Get query analytics for the last N days."""
    client = get_mongo_client()
    if not client.enabled or not client.queries:
        return {}

    try:
        since = datetime.utcnow() - timedelta(days=days)
        pipeline = [
            {"$match": {"timestamp": {"$gte": since}}},
            {
                "$group": {
                    "_id": None,
                    "total_queries": {"$sum": 1},
                    "avg_response_time_ms": {"$avg": "$response_time_ms"},
                    "groq_calls": {"$sum": {"$cond": ["$groq_api_called", 1, 0]}},
                    "intents": {"$push": "$intent_detected"},
                    "data_sources": {"$push": "$data_sources_used"},
                }
            }
        ]
        result = list(client.queries.aggregate(pipeline))
        if result:
            return result[0]
        return {}
    except Exception as e:
        print(f"[MongoDB] Failed to get analytics: {e}")
        return {}
