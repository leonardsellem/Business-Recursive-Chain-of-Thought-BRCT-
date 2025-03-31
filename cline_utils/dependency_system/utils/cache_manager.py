"""
Cache management module with dynamic, TTL-based caching for dependency tracking system.
Supports on-demand cache creation, automatic expiration, and granular invalidation.
"""

import functools
import os
import time
import re
import json
from typing import Dict, Any, Callable, TypeVar, Optional, List, Tuple
import logging

from .path_utils import normalize_path

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])

# Configuration
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
DEFAULT_MAX_SIZE = 1000  # Default max items per cache
DEFAULT_TTL = 600  # 10 minutes in seconds
CACHE_SIZES = {
    "embeddings_generation": 100,  # Smaller for heavy data
    "key_generation": 5000,        # Larger for key maps
    "default": DEFAULT_MAX_SIZE
}

class Cache:
    """A single cache instance with LRU eviction, per-entry TTL, and dependency tracking."""
    def __init__(self, name: str, ttl: int = DEFAULT_TTL, max_size: int = DEFAULT_MAX_SIZE):
        self.name = name
        self.data: Dict[str, Tuple[Any, float, Optional[float]]] = {}  # (value, access_time, expiry_time)
        self.dependencies: Dict[str, List[str]] = {}  # key -> dependent keys
        self.reverse_deps: Dict[str, List[str]] = {}  # key -> keys that depend on it
        self.creation_time = time.time()
        self.default_ttl = ttl
        self.max_size = CACHE_SIZES.get(name, max_size)
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Any:
        if key in self.data:
            value, _, expiry = self.data[key]
            if expiry is None or time.time() < expiry:
                self.data[key] = (value, time.time(), expiry)  # Update access time
                self.hits += 1
                return value
            else:
                del self.data[key]
                if key in self.reverse_deps:
                    del self.reverse_deps[key]
        self.misses += 1
        return None

    def set(self, key: str, value: Any, dependencies: Optional[List[str]] = None, ttl: Optional[int] = None) -> None:
        if len(self.data) >= self.max_size:
            self._evict_lru()
        expiry = time.time() + (ttl if ttl is not None else self.default_ttl) if ttl != 0 else None
        self.data[key] = (value, time.time(), expiry)
        if dependencies:
            for dep in dependencies:
                if dep not in self.dependencies:
                    self.dependencies[dep] = []
                self.dependencies[dep].append(key)
                if key not in self.reverse_deps:
                    self.reverse_deps[key] = []
                self.reverse_deps[key].append(dep)

    def _evict_lru(self) -> None:
        if not self.data:
            return
        lru_key = min(self.data, key=lambda k: self.data[k][1])
        self._remove_key(lru_key)

    def _remove_key(self, key: str) -> None:
        if key in self.data:
            del self.data[key]
        if key in self.reverse_deps:
            for dep in self.reverse_deps[key]:
                if dep in self.dependencies and key in self.dependencies[dep]:
                    self.dependencies[dep].remove(key)
                if dep in self.dependencies and not self.dependencies[dep]:
                    del self.dependencies[dep]
            del self.reverse_deps[key]

    def cleanup_expired(self) -> None:
        """Remove all expired entries."""
        expired_keys = [k for k, (_, _, expiry) in self.data.items() if expiry and time.time() > expiry]
        for key in expired_keys:
            self._remove_key(key)

    def is_expired(self) -> bool:
        return (time.time() - self.creation_time) > self.default_ttl and not self.data

    def invalidate(self, key_pattern: str) -> None:
        """Invalidate entries matching a key pattern (supports regex)."""
        compiled_pattern = re.compile(key_pattern)
        keys_to_remove = [k for k in self.data if compiled_pattern.match(k)]
        for key in keys_to_remove:
            self._remove_key(key)
            if key in self.dependencies:
                dependent_keys = self.dependencies.pop(key)
                for dep_key in dependent_keys:
                    self._remove_key(dep_key)

    def stats(self) -> Dict[str, int]:
        return {"hits": self.hits, "misses": self.misses, "size": len(self.data)}

class CacheManager:
    """Manages multiple caches with persistence and cleanup."""
    def __init__(self, persist: bool = False):
        self.caches: Dict[str, Cache] = {}
        self.persist = persist
        if persist:
            os.makedirs(CACHE_DIR, exist_ok=True)
            self._load_persistent_caches()

    def get_cache(self, cache_name: str, ttl: int = DEFAULT_TTL) -> Cache:
        """Retrieve or create a cache by name."""
        if cache_name not in self.caches or self.caches[cache_name].is_expired():
            self.caches[cache_name] = Cache(cache_name, ttl)
            logger.debug(f"Spun up new cache: {cache_name} with TTL {ttl}s")
        return self.caches[cache_name]

    def cleanup(self) -> None:
        """Remove expired caches."""
        expired = [name for name, cache in self.caches.items() if cache.is_expired()]
        for name in expired:
            if self.persist:
                self._save_cache(name)
            del self.caches[name]
            logger.debug(f"Spun down expired cache: {name}")
        for cache in self.caches.values():
            cache.cleanup_expired()

    def clear_all(self) -> None:
        if self.persist:
            for name in self.caches:
                self._save_cache(name)
        self.caches.clear()
        logger.info("All caches cleared.")

    def _save_cache(self, cache_name: str) -> None:
        if cache_name in self.caches:
            cache_file = os.path.join(CACHE_DIR, f"{cache_name}.json")
            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    data = {
                        "data": {k: v[0] for k, v in self.caches[cache_name].data.items() if v[2] is None or v[2] > time.time()},
                        "dependencies": self.caches[cache_name].dependencies
                    }
                    json.dump(data, f)
            except Exception as e:
                logger.error(f"Failed to save cache {cache_name}: {e}")

    def _load_persistent_caches(self) -> None:
        for cache_file in os.listdir(CACHE_DIR):
            if cache_file.endswith('.json'):
                cache_name = cache_file[:-5]
                try:
                    with open(os.path.join(CACHE_DIR, cache_file), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        cache = Cache(cache_name)
                        for key, value in data["data"].items():
                            cache.set(key, value)  # No TTL for reloaded items
                        cache.dependencies = data.get("dependencies", {})
                        self.caches[cache_name] = cache
                    logger.debug(f"Loaded persistent cache: {cache_name}")
                except Exception as e:
                    logger.error(f"Failed to load cache {cache_name}: {e}")

cache_manager = CacheManager(persist=False)  # Toggle to True for persistence

def get_tracker_cache_key(tracker_path: str, tracker_type: str) -> str:
    return f"tracker:{normalize_path(tracker_path)}:{tracker_type}"

def clear_all_caches() -> None:
    """Clear all caches in the manager."""
    cache_manager.clear_all()

def invalidate_dependent_entries(cache_name: str, key: str) -> None:
    """Invalidate cache entries matching a key pattern."""
    cache = cache_manager.get_cache(cache_name)
    cache.invalidate(key)

def file_modified(file_path: str, project_root: str, cache_type: str = "all") -> None:
    """Invalidate caches when a file is modified."""
    norm_path = normalize_path(file_path)
    norm_root = normalize_path(project_root)
    key = f".*:{norm_path}:.*" if cache_type == "all" else f"{cache_type}:{norm_path}:.*"
    for cache_name in cache_manager.caches:
        invalidate_dependent_entries(cache_name, key)

def tracker_modified(tracker_path: str, tracker_type: str, project_root: str, cache_type: str = "all") -> None:
    """Invalidate caches when a tracker is modified."""
    norm_path = normalize_path(tracker_path)
    key = get_tracker_cache_key(tracker_path, tracker_type) if cache_type == "all" else f"{cache_type}:{norm_path}:.*"
    invalidate_dependent_entries("tracker", key)

def cached(cache_name: str, key_func: Optional[Callable] = None, ttl: Optional[int] = DEFAULT_TTL):
    """Decorator for caching with dynamic dependencies and TTL."""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = key_func(*args, **kwargs) if key_func else f"{func.__name__}:{str(args)}:{str(kwargs)}"
            cache = cache_manager.get_cache(cache_name, ttl)
            result = cache.get(key)
            if result is not None:
                #logger.debug(f"Cache hit: {cache_name}:{key}")
                return result
            #logger.debug(f"Cache miss: {cache_name}:{key}")
            result = func(*args, **kwargs)
            dependencies = []
            if isinstance(result, tuple) and len(result) == 2 and isinstance(result[1], list):
                value, dependencies = result
            else:
                value = result
                if func.__name__ in ['load_embedding', 'load_metadata', 'analyze_file', 'analyze_project', 'get_file_type']:
                    if args and isinstance(args[0], str):
                        dependencies.append(f"file:{normalize_path(args[0])}")
            cache.set(key, value, dependencies, ttl)
            cache_manager.cleanup()
            return value
        return wrapper
    return decorator

def check_file_modified(file_path: str) -> bool:
    """Check if a file has been modified, updating metadata cache."""
    norm_path = normalize_path(file_path)
    cache_key = f"timestamp:{norm_path}"
    cache = cache_manager.get_cache("metadata")
    if not os.path.exists(file_path):
        return False
    current_timestamp = os.path.getmtime(file_path)
    cached_data = cache.get(cache_key)
    if cached_data is None:
        cache.set(cache_key, current_timestamp)
        return False
    if current_timestamp > cached_data:
        cache.set(cache_key, current_timestamp)
        from .path_utils import get_file_type
        file_type = get_file_type(file_path)
        # file_modified(file_path, os.path.dirname(file_path), file_type)
        return True
    return False

# @cached('file_type_cache', key_func=lambda file_path: f"file_type:{normalize_path(file_path)}:{os.path.getmtime(file_path) if os.path.exists(file_path) else 'missing'}")
def get_file_type_cached(file_path: str) -> str:
    """Cached version of get_file_type."""
    from .path_utils import get_file_type
    return get_file_type(file_path)

def get_cache_stats(cache_name: str) -> Dict[str, int]:
    """Get hit/miss stats for a cache."""
    cache = cache_manager.get_cache(cache_name)
    return cache.stats()