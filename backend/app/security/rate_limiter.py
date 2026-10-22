import time
from collections import defaultdict
from typing import Dict, List
from fastapi import Request, HTTPException, status
from backend.app.config import settings


class InMemoryRateLimiter:
    """
    Sliding window rate limiter to throttle abusive requests per client IP.
    """
    def __init__(self, requests_per_minute: int = 120):
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60
        self.client_records: Dict[str, List[float]] = defaultdict(list)

    def is_rate_limited(self, client_ip: str) -> bool:
        now = time.time()
        timestamps = self.client_records[client_ip]

        # Prune timestamps outside window
        valid_timestamps = [t for t in timestamps if now - t < self.window_seconds]
        valid_timestamps.append(now)
        self.client_records[client_ip] = valid_timestamps

        return len(valid_timestamps) > self.requests_per_minute


rate_limiter = InMemoryRateLimiter(requests_per_minute=settings.RATE_LIMIT_PER_MINUTE)


async def check_rate_limit(request: Request):
    client_ip = request.client.host if request.client else "127.0.0.1"
    if rate_limiter.is_rate_limited(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait before retrying.",
            headers={"Retry-After": "60"},
        )
