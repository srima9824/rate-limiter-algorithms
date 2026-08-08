from token_bucket import TokenBucket
import threading
import time

class RateLimiter:
    def __init__(
            self, 
            max_tokens: int, 
            refill_rate: float, 
            cleanup_interval: int = 300, 
            expiry_seconds: int = 1800):

        if max_tokens <= 0:
            raise ValueError("Max Tokens must be positive.")
        if refill_rate <= 0:
            raise ValueError("Refill Rate must be positive.")
        
        self._max_tokens = max_tokens 
        self._refill_rate = refill_rate
        self._buckets: dict[str, TokenBucket] = {} # in-memory cache
        self._lock = threading.Lock()
        self._cleanup_interval = cleanup_interval
        self._expiry_seconds = expiry_seconds
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_worker,
            daemon=True
        )
        self._cleanup_thread.start()

    def _get_bucket(self, key:str) -> TokenBucket:
        # Create a new bucket for a first time user, else return an existing bucket
        # Bucket Creation should be Atomic
        with self._lock:
            if key not in self._buckets:
                self._buckets[key] = TokenBucket(self._max_tokens, self._refill_rate)
            return self._buckets[key]

    def _cleanup_inactive_buckets(self, expiry_seconds: int) -> None:
            with self._lock:
                current_time = time.time()
                keys_to_delete = []
                for key, bucket in self._buckets.items():
                    last_activity = bucket.get_last_refill_time()
                    if current_time - last_activity >= expiry_seconds:
                        keys_to_delete.append(key)
                for key in keys_to_delete:
                    del self._buckets[key]

    def _cleanup_worker(self):
        # Timely cleanup of buckets needed to prevent memory leaks
        while True:
            time.sleep(self._cleanup_interval)
            self._cleanup_inactive_buckets(self._expiry_seconds)

    def allow_request(self, key: str, tokens: int = 1) -> tuple[bool ,float, float]:
        if not isinstance(key, str):
            raise TypeError("Key must be of type str")
        if tokens <= 0:
            raise ValueError("Tokens must be positive")
        bucket = self._get_bucket(key)
        return bucket.consume(tokens)
