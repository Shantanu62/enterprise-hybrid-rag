import redis
from redisvl.extensions.cache.llm import SemanticCache
from app.config import settings


class SemanticCacheManager:
    def __init__(self, distance_threshold: float = 0.1):
        # Connect to Redis instance
        self.redis_client = redis.Redis.from_url(settings.REDIS_URL)

        # Setup RedisVL Semantic Cache
        try:
            self.cache = SemanticCache(
                name="rag_semantic_cache",
                redis_client=self.redis_client,
                distance_threshold=distance_threshold
            )
        except Exception as e:
            print(f"Semantic cache init failed: {e}")
            self.cache = None

    def get(self, prompt: str):
        """Return cached answer text if a similar query exists, else None."""
        if self.cache is None:
            return None
        try:
            results = self.cache.check(prompt=prompt, num_results=1)
            if results:
                return results[0].get("response")
        except Exception as e:
            print(f"Semantic cache get failed: {e}")
        return None

    def set(self, prompt: str, response: str):
        """Store a query and its answer in the cache."""
        if self.cache is None:
            return
        try:
            self.cache.store(prompt=prompt, response=response)
        except Exception as e:
            print(f"Semantic cache set failed: {e}")