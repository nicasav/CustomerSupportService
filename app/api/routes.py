from fastapi import APIRouter, HTTPException, Request, status

from app.api.schemas import (
    DecisionRequest,
    FinalResponse,
    RequestCreate,
    RequestResponse,
)
from app.services.ticket_service import (
    AlreadyResolvedError,
    InvalidReferenceError,
)

"""FastAPI routes for health, request creation, and HITL decisions."""

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """Return a lightweight liveness response for the service."""
    return {"status": "ok"}


@router.post(
    "/requests",
    response_model=RequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_request(
    payload: RequestCreate,
    request: Request,
) -> RequestResponse:
    """Start a workflow and return either a final or pending response."""
    return await request.app.state.ticket_service.start(payload)


@router.post(
    "/requests/{reference}/decision",
    response_model=FinalResponse,
)
async def decide_request(
    reference: str,
    payload: DecisionRequest,
    request: Request,
) -> FinalResponse:
    """Resume a pending workflow with a support specialist's decision."""
    try:
        return await request.app.state.ticket_service.resume(reference, payload)
    except InvalidReferenceError as exc:
        raise HTTPException(status_code=404, detail="Unknown request reference") from exc
    except AlreadyResolvedError as exc:
        raise HTTPException(status_code=409, detail="Request is already resolved") from exc
