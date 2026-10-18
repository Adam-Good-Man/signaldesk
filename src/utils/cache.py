import threading
import time
from typing import Any, Optional, Dict, Tuple
from dataclasses import dataclass

# Global cache instance
global_cache: Optional['Cache'] = None

@dataclass
class CacheItem:
    """Represents a single item in the cache"""
    value: Any
    expiration: float  # Unix timestamp when the item expires

class Cache:
    """Thread-safe cache implementation with expiration support"""
    
    def __init__(self):
        """Initialize a new cache instance"""
        self._items: Dict[str, CacheItem] = {}
        self._lock = threading.RLock()  # Using RLock for reentrant locking
    
    def set(self, key: str, value: Any, duration: float) -> None:
        """
        Add a value to the cache with expiration
        
        Args:
            key: The key to store the value under
            value: The value to store
            duration: Expiration time in seconds
        """
        with self._lock:
            self._items[key] = CacheItem(
                value=value,
                expiration=time.time() + duration
            )
    
    def get(self, key: str) -> Tuple[Any, bool]:
        """
        Retrieve a value from the cache
        
        Args:
            key: The key to look up
            
        Returns:
            Tuple of (value, found) where found is a boolean indicating if the key exists
            and hasn't expired
        """
        with self._lock:
            item = self._items.get(key)
            if item is None:
                return None, False
            
            if time.time() > item.expiration:
                del self._items[key]
                return None, False
            
            return item.value, True
    
    def delete(self, key: str) -> None:
        """
        Remove a value from the cache
        
        Args:
            key: The key to remove
        """
        with self._lock:
            self._items.pop(key, None)

def init_global_cache() -> None:
    """Initialize the global cache instance"""
    global global_cache
    global_cache = Cache()

# 直接初始化全局缓存，确保所有模块导入时都可用
init_global_cache()

# Example usage
if __name__ == "__main__":
    # Initialize global cache
    init_global_cache()
    
    # Example operations
    cache = global_cache
    
    # Set a value that expires in 5 seconds
    cache.set("test_key", "test_value", 5.0)
    
    # Get the value
    value, found = cache.get("test_key")
    if found:
        print(f"Found value: {value}")
    
    # Wait for expiration
    time.sleep(6)
    
    # Try to get expired value
    value, found = cache.get("test_key")
    if not found:
        print("Value has expired")
    
    # Delete a value
    cache.delete("test_key") 