import time
import threading

class TokenBucket:
    def __init__(self, max_tokens: int, refill_rate: float):
        if max_tokens <= 0:
            raise ValueError("Max Tokens must be positive.")
        if refill_rate <= 0:
            raise ValueError("Refill Rate must be positive.")

        self._max_tokens = max_tokens
        self._current_tokens = max_tokens
        self._refill_rate = refill_rate # no of tokens added to bucket/second
        self._last_refill_time = time.time()
        self._lock = threading.Lock() # every bucket has its own lock

    def _refill(self) -> None:
        # Two approaches possible
        # Approach 1 : Assume refill() is called every second, in that case
        # self.current_tokens = min(max_tokens, refill_rate)
        # In this case the assumptions is self.refill_interval is always 1s
        # However, this is not a production efficient approach

        # Approach 2: Lazy Refilling, more production ready
        # Calculate No of Tokens to be added
        current_time = time.time()
        elapsed_time_after_last_refill = current_time - self._last_refill_time
        tokens_to_add = elapsed_time_after_last_refill * self._refill_rate

        # Update tokens
        self._current_tokens = min(self._max_tokens, self._current_tokens + tokens_to_add)
        self._last_refill_time = current_time

    def _get_retry_after(self, remaining: float, tokens_per_request: int = 1) -> float:
        # How long until I have {tokens} no of tokens in my bucket?
        # Time = Work / Rate
        # Work = Tokens still needed
        # Rate = Tokens refilled per second
        # Therefore,
        #   Retry After = Tokens Needed / Refill Rate
        if remaining >= tokens_per_request:
            return 0.0

        tokens_needed = tokens_per_request - remaining
        retry_after = tokens_needed / self._refill_rate

        return retry_after

    def consume(self, tokens_per_request: int = 1) -> tuple[bool, float, float]:
        # Sync bucket with latest time and add tokens to bucket if necessary
        # Avoid Race Conditions , enable multithreaded processing
        # Tokens is kept for future use, in case we want to make expenses of different api's different
        # store self._current_tokens in a variable (remaining) and pass it across functions to maintain atomicity
        with self._lock: 
            self._refill()
            remaining_tokens = self._current_tokens
            if remaining_tokens >= tokens_per_request:
                self._current_tokens -= tokens_per_request
                remaining_tokens = self._current_tokens
                return True, remaining_tokens, 0.0
            else:
                return False, remaining_tokens, self._get_retry_after(remaining_tokens, tokens_per_request)

    def get_last_refill_time(self) -> time:
        with self._lock:
            return self._last_refill_time
    