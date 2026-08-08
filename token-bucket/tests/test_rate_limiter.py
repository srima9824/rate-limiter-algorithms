from rate_limiter import RateLimiter
import pytest

# We want to verify that incorrect values raise value errors
def test_max_tokens_must_be_positive():
    with pytest.raises(ValueError):
        RateLimiter(max_tokens=-2, refill_rate=2)
    with pytest.raises(ValueError):
        RateLimiter(max_tokens=0, refill_rate=12)

def test_refill_rate_must_be_positive():
    with pytest.raises(ValueError):
        RateLimiter(max_tokens=5, refill_rate=0)
    with pytest.raises(ValueError):
        RateLimiter(max_tokens=5, refill_rate=-9)

def test_request_key_must_be_string():
    rate_limiter = RateLimiter(5,2)
    with pytest.raises(TypeError):
        rate_limiter.allow_request(123)

def test_tokens_must_be_positive():
    rate_limiter = RateLimiter(5,2)     
    with pytest.raises(ValueError):
        rate_limiter.allow_request('127.0.0.1', 0)
    with pytest.raises(ValueError):
        rate_limiter.allow_request('127.0.0.1', -2)

# Test allow_request functionality
def test_first_request_creates_bucket_and_is_allowed():
    rate_limiter = RateLimiter(5,2) 
    allowed, remaining, retry_after = rate_limiter.allow_request('127.0.0.1')

    assert allowed is True
    assert remaining == pytest.approx(4, abs=0.0001)
    assert retry_after == 0.0

def test_token_reduction_when_same_client_requests():
    rate_limiter = RateLimiter(5,2) 
    allowed, remaining, retry_after = rate_limiter.allow_request('127.0.0.1')
    allowed, remaining, retry_after = rate_limiter.allow_request('127.0.0.1')

    assert allowed is True
    assert remaining == pytest.approx(3, abs=0.0001)
    assert retry_after == 0.0

def test_allow_request_returns_retry_after_when_rate_limited(monkeypatch):
    monkeypatch.setattr("token_bucket.time.time", lambda: 100)

    rate_limiter = RateLimiter(2, 2)

    rate_limiter.allow_request("127.0.0.1")
    rate_limiter.allow_request("127.0.0.1")

    allowed, remaining, retry_after = rate_limiter.allow_request("127.0.0.1")

    assert allowed is False
    assert remaining == 0
    assert retry_after == 0.5