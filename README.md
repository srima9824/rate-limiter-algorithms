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
- Think about production concerns such as memory cleanup, logging, graceful degradation and middleware integration.
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
          Get/Create Bucket
                   │
                   ▼
      TokenBucket.consume()
                   │
         Acquire Bucket Lock
                   │
              Lazy Refill
                   │
          Consume Token
                   │
                   ▼
    (Allowed?, Remaining?, RetryAfter?)
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

# Request Flow

Every incoming request follows the following sequence:

1. Middleware intercepts the request.
2. Client identifier is extracted.
3. RateLimiter fetches (or creates) a TokenBucket.
4. Bucket synchronizes itself using Lazy Refill.
5. Bucket decides whether request can proceed.
6. Middleware either

   - returns **429 Too Many Requests**

   OR

   - forwards request to FastAPI endpoint.

7. Response headers are added.
8. Response is returned.

---

# Token Bucket Algorithm

Every client owns an independent bucket.

```
Maximum Capacity = 10 Tokens

Current Tokens = 10
```

Each request consumes one token.

```
10

↓

9

↓

8

↓

...
```

Once the bucket becomes empty,

```
Current Tokens = 0
```

future requests are rejected until enough tokens have been regenerated.

---

# Lazy Refill

Instead of continuously adding tokens every second,

tokens are regenerated **only when a request arrives.**

Example:

```
Refill Rate = 2 tokens/sec

User waits 5 seconds

↓

Next Request

↓

Tokens Added = 10
```

This avoids running unnecessary background refill jobs.

---

# Why Lazy Refill?

Two possible approaches were considered.

## Approach 1

Continuously refill every bucket every second.

Pros

- Easy to understand.

Cons

- Requires a scheduler.
- Wastes CPU even when nobody is using the API.
- Does not scale well.

---

## Approach 2 (Chosen)

Calculate elapsed time only when a request arrives.

```
Tokens Added

=

Elapsed Time

×

Refill Rate
```

Advantages

- O(1)
- No scheduler
- Scales much better

---

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

Although internally fractional values are stored,

every API request consumes **whole tokens only.**

This keeps the refill accurate while keeping API cost intuitive.

---

# Thread Safety

Multiple users may hit the server simultaneously.

Without synchronization,

two requests may both read

```
Current Tokens = 1
```

Both succeed.

Bucket becomes

```
-1 Tokens
```

which is incorrect.

To avoid race conditions,

every TokenBucket owns its own lock.

```
Bucket A

🔒

Bucket B

🔒

Bucket C

🔒
```

Requests belonging to different users proceed concurrently.

Only requests targeting the same bucket wait.

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

Originally,

remaining tokens were retrieved using

```
consume()

↓

get_remaining_tokens()
```

This introduced a race condition.

Another thread could modify the bucket before remaining tokens were read.

The implementation was changed to return

```
Allowed?

Remaining Tokens

Retry After
```

directly from

```
consume()
```

ensuring the entire operation happens under a single lock.

---

# Retry-After

When a request cannot be served,

the server calculates

```
Retry After

=

Tokens Needed

/

Refill Rate
```

instead of returning an arbitrary delay.

This tells the client exactly when another request is likely to succeed.

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

Since every request triggers a refill,

this timestamp also acts as the bucket's last activity timestamp.

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

If the rate limiter itself encounters an unexpected error,

the request is still forwarded to the application.

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
- Sliding Window Log
- Fixed Window
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
