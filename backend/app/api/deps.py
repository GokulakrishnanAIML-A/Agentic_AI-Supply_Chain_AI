from fastapi import Header, HTTPException

from app.core.config import settings


def current_planner(x_api_key: str | None = Header(None, alias="X-API-Key")) -> str:
    """Extract authenticated reviewer name from X-API-Key header.
    Throws 401 if missing or unmapped.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing required authentication header 'X-API-Key'",
        )
    planners = settings.planners
    if x_api_key not in planners:
        raise HTTPException(
            status_code=401,
            detail="Invalid 'X-API-Key' provided",
        )
    return planners[x_api_key]
