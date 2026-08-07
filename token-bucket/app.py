from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from config import settings
from rate_limiter import RateLimiter
from helpers import get_client_identifier
import math
import logging

app = FastAPI()
logger = logging.getLogger(__name__)
rate_limiter = RateLimiter(
    max_tokens=settings.max_tokens,
    refill_rate=settings.refill_rate,
    cleanup_interval=settings.bucket_cleanup_interval,
    expiry_seconds=settings.bucket_expiry_seconds
)


def _add_rate_limit_headers(response: Response, limit: int, remaining_tokens: float, retry_after: float) -> None:
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining_tokens)
    response.headers["Retry-After"] = str(math.ceil(retry_after))


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    # Phase 1: Before endpoint, Inspect/validate the REQUEST
    remaining_tokens = None
    retry_after = None
    try:
        client_id = get_client_identifier(request)
        req_allowed, remaining_tokens, retry_after = rate_limiter.allow_request(client_id)
        
        if not req_allowed:
            response = JSONResponse(
                status_code=429,
                content={"message": "Rate limit exceeded"}
            )
            _add_rate_limit_headers(response, settings.max_tokens, remaining_tokens,  retry_after)
            return response
    except Exception as e:
        logger.exception(e)

    # Phase 2: After endpoint, Modify/log the RESPONSE
    response = await call_next(request)
    if remaining_tokens is not None:
        _add_rate_limit_headers(response, settings.max_tokens, remaining_tokens,  retry_after)
    return response

@app.get("/")
async def root():
    return {"message": "Srima's Rate Limited Sample App!"}
