from typing import Optional
from fastapi import Header, HTTPException, status, Security
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from backend.app.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


async def verify_admin_api_key(
    api_key: Optional[str] = Security(api_key_header),
    auth: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> str:
    """
    Enforces authentication for write, update, and delete administrative endpoints.
    Accepts either X-API-Key header or Authorization: Bearer <token>.
    """
    token = api_key or (auth.credentials if auth else None)
    if not token or token != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Provide valid X-API-Key header or Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token
