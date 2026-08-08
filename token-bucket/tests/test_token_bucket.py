import pytest
from token_bucket import TokenBucket

# A new bucket with 3 tokens should allow 3 requests.
def test_new_bucket_starts_with_max_tokens():
    bucket = TokenBucket(max_tokens=3, refill_rate=1)

    assert bucket.consume(1)[0] is True
    assert bucket.consume(1)[0] is True
    assert bucket.consume(1)[0] is True

    assert bucket.consume(1)[0] is False

# We want to verify that inputs values raise value errors
def test_max_tokens_must_be_positive():
    with pytest.raises(ValueError):
        TokenBucket(max_tokens=-2, refill_rate=2)
    with pytest.raises(ValueError):
        TokenBucket(max_tokens=0, refill_rate=12)

def test_refill_rate_must_be_positive():
    with pytest.raises(ValueError):
        TokenBucket(max_tokens=5, refill_rate=0)
    with pytest.raises(ValueError):
        TokenBucket(max_tokens=5, refill_rate=-9)

# Does consuming a token actually reduce the bucket correctly
def test_consuming_token_reduces_remaining_tokens():
    bucket = TokenBucket(max_tokens=5, refill_rate=1)

    allowed, remaining, retry_after = bucket.consume(1)

    assert allowed is True
    assert remaining == 4
    assert retry_after == 0.0

# Test what happens when there are not enough tokens in bucket
def test_bucket_tokens_not_enough():
    bucket = TokenBucket(max_tokens=2, refill_rate=2)

    allowed, remaining, retry_after = bucket.consume(3)

    assert allowed is False
    assert remaining == 2
    assert retry_after == 0.5

# If time passes, the bucket should regenerate tokens when the next consume() happens.
def test_bucket_refills_after_time_passes(monkeypatch):
    monkeypatch.setattr("token_bucket.time.time", lambda: 100)

    bucket = TokenBucket(max_tokens=5, refill_rate=2)

    # Bucket was created at t = 100.
    # Consume all 5 tokens.
    for _ in range(5):
        bucket.consume(1)

    # Move the clock forward by exactly 1 second.
    monkeypatch.setattr("token_bucket.time.time", lambda: 101)

    allowed, remaining, retry_after = bucket.consume(1)

    assert allowed is True
    assert remaining == pytest.approx(1)
    assert retry_after == 0.0
