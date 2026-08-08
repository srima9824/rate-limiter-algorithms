# Token Bucket Rate Limiter

A production-inspired implementation of the **Token Bucket Rate Limiting Algorithm** using **FastAPI** and **Python**.

This project is not just an implementation of the algorithm—it focuses on writing maintainable, thread-safe, production-oriented code while understanding the engineering decisions behind it.

---

# Motivation

Most Token Bucket implementations available online focus only on making the algorithm work.

While building this project, the objective was different:

- Write clean, modular code.
- Apply Object Oriented Design principles.
- Handle concurrent requests safely.
- Keep the implementation configurable.
- Think about production concerns such as memory cleanup, logging, graceful degradation, exception handling and middleware integration.
- Understand **why** every design decision was made instead of simply writing code that works.

---

# Features

- Token Bucket Rate Limiting
- Lazy Token Refill
- Fractional Token Refill
- Integer Token Consumption
- Thread-safe Bucket Operations
- Per-client Buckets
- Automatic Bucket Cleanup
- Retry-After Response Header
- FastAPI Middleware Integration
- Environment Based Configuration
- Graceful Failure (Fail Open)

---

# Project Structure

```
token-bucket/
│
├── app.py
├── config.py
├── helpers.py
├── rate_limiter.py
├── token_bucket.py
├── requirements.txt
├── .env
└── README.md
```

---

# High Level Architecture

```
                Client
                   │
                   ▼
           FastAPI Middleware
                   │
                   ▼
        Extract Client Identifier
                   │
                   ▼
        RateLimiter.allow_request()
                   │
                   ▼
    Get/Create Bucket (_get_bucket())
            |
            ├── Acquire RateLimiter Lock
            │
            ├── Lookup/Create Bucket
            │
            └── Release RateLimiter Lock
                    ▼
    TokenBucket (bucket.consume())
            │
            ├── Acquire Bucket Lock
            │
            ├── _refill()
            │
            ├── Check remaining tokens
            │
            ├── Consume token (if allowed)
            │
            ├── Calculate retry_after
            │
            ├── Return (allowed, remaining, retry_after)
            │
            └── Release Bucket Lock
                   |
                   ▼
    Return (Allowed?, Remaining?, RetryAfter?)
                   │
                   ▼
          Middleware Response
                   │
         Add Rate Limit Headers
                   │
                   ▼
                Client
```
---

# Token Bucket Algorithm

Every client owns an independent bucket. For this project we maintain an in memory cache of the form { 'ip': 'TokenBucket' }

Each bucket maintains:

- Maximum Capacity (`max_tokens`): Maximum amount of tokens allowed in the bucket
- Current Tokens (`current_tokens`): Remaining amount of tokens in the bucket
- Refill Rate (`refill_rate`): At rate (tokens/second) the bucket should be refilled 
- Last Refill Timestamp (`last_refill_time`): What was the last time when bucket was refilled

For the sake of simplicity, each request consumes 1 token. 

For every incoming request, the following algorithm is executed:

### Step 1: Locate Bucket
- Fetch the client's bucket.
- If it does not exist, create a new bucket with `max_tokens`.

### Step 2: Lazy Refill
- Calculate the elapsed time since the previous refill.
- Compute the number of tokens to add.

```
tokens_to_add = elapsed_time × refill_rate
```

- Update the bucket.

```
current_tokens = min(max_tokens,
                     current_tokens + tokens_to_add)
```

- Update `last_refill_time`.

### Step 3: Check Capacity

If

```
current_tokens >= tokens_requested
```

- Consume the requested tokens.
- Allow the request.

Otherwise,

- Reject the request.
- Calculate

```
retry_after = (tokens_requested - current_tokens)
              / refill_rate
```

- Return the time after which the request can be retried.

### Step 4: Return Result

The bucket returns a single atomic response containing:

- Whether the request was allowed.
- Remaining tokens after processing.
- Retry-After duration (if rejected).
---

# Why Lazy Refill?

Two possible approaches were considered before implementing the Token Bucket algorithm.

| Aspect | Periodic Refill | Lazy Refill (Chosen) |
|--------|-----------------|----------------------|
| **How it works** | Refill every bucket at fixed intervals (e.g. every second). | Refill a bucket only when a request arrives. |
| **Scheduler Required?** | ✅ Yes | ❌ No |
| **CPU Usage** | Keeps running even when there are no requests. | Performs work only when required. |
| **Scalability** | Poor for a large number of buckets. | Scales well since work is proportional to incoming traffic. |
| **Implementation Complexity** | Requires background scheduling. | Simpler implementation. |
| **Time Complexity / Request** | O(1) refill + scheduler overhead. | O(1) |
| **Chosen?** | ❌ No | ✅ Yes |

# Fractional Tokens

The implementation allows fractional tokens internally.

Example

```
Refill Rate

=

0.5 Tokens / Second
```

After

```
3 Seconds
```

Bucket contains

```
1.5 Tokens
```

Although internally fractional values are stored, every API request consumes **whole tokens only.** This keeps the refill accurate while keeping API cost intuitive.

---

# Thread Safety

Multiple users may hit the server simultaneously. Without synchronization, two requests may both read

```
Current Tokens = 1
```

Both succeed. Bucket becomes

```
-1 Tokens
```

which is incorrect. To avoid race conditions, every TokenBucket owns its own lock.

```
Bucket A

🔒

Bucket B

🔒

Bucket C

🔒
```

Requests belonging to different users proceed concurrently. Only requests targeting the same bucket wait.

---

# Why another lock inside RateLimiter?

TokenBucket lock protects

```
Current Tokens
Last Refill Time
```

RateLimiter lock protects

```
Dictionary of Buckets
```

These are two completely different shared resources.

---

# Atomicity

Originally, remaining tokens were retrieved using

```
consume()

↓

get_remaining_tokens()
```

This introduced a race condition. Another thread could modify the bucket before remaining tokens were read. The implementation was changed to return

```
(Allowed? , Remaining Tokens, Retry After)

directly from consume()
```

ensuring the entire operation happens under a single lock.

---

# Retry-After

When a request cannot be served, the server calculates

```
Retry After = Tokens Needed / Refill Rate
```

instead of returning an arbitrary delay. This tells the client exactly when another request is likely to succeed.

---

# Middleware

Rate limiting is implemented as FastAPI middleware.

Reasons

- Every request automatically passes through it.
- Business logic remains unaware of rate limiting.
- Easy to replace with another algorithm later.

---

# Bucket Cleanup

Inactive users should not occupy memory forever.

Every bucket stores

```
Last Refill Time
```

Since every request triggers a refill, this timestamp also acts as the bucket's last activity timestamp. 

A daemon thread periodically removes buckets that have remained inactive beyond a configurable duration.

---

# Why a Daemon Thread?

A normal thread keeps Python alive.

A daemon thread automatically exits when the application exits.

Cleanup should never prevent the server from shutting down.

---

# Configuration

All configurable values are kept outside the code.

```
MAX_TOKENS

REFILL_RATE

TOKENS_PER_REQUEST

BUCKET_CLEANUP_INTERVAL

BUCKET_EXPIRY_SECONDS
```

This avoids hardcoded values and allows different deployments to use different limits.

---

# Error Handling

The middleware follows a **Fail Open** strategy.

If the rate limiter itself encounters an unexpected error, the request is still forwarded to the application.

Reason

Availability is generally considered more important than temporarily disabling rate limiting.

Errors are logged for investigation.

---

# Object Oriented Design

The project intentionally separates responsibilities.

## TokenBucket

Responsible for

- Bucket State
- Lazy Refill
- Token Consumption
- Retry Calculation

---

## RateLimiter

Responsible for

- Bucket Management
- Client Lookup
- Cleanup Scheduling

---

## Middleware

Responsible for

- Request Interception
- Response Headers
- Returning 429 Responses

---

Each class owns a single responsibility.

---

# Best Practices Used

- Encapsulation
- Single Responsibility Principle
- Thread Safety
- Lazy Evaluation
- Environment Driven Configuration
- Middleware Pattern
- Graceful Degradation
- Atomic Operations
- Modular Design
- Type Hinting
- Helper Functions
- Private Members
- Response Headers
- Logging

---

# Future Improvements

- Redis-backed distributed rate limiting
- Multiple rate limiting algorithms
- Sliding Window Counter
- Leaky Bucket
- Different rate limits for premium users
- Different token cost per endpoint
- Metrics using Prometheus
- Grafana Dashboard
- Distributed Cleanup

---

# What I Learned

This project helped me understand

- Token Bucket algorithm
- Designing thread-safe code
- Why atomic operations matter
- Lock granularity
- Middleware architecture
- Lazy evaluation
- Background daemon threads
- Configuration management
- Graceful error handling
- Thinking beyond "code that works" towards "code that scales"

---
