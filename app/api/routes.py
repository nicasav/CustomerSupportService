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

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
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
    try:
        return await request.app.state.ticket_service.resume(reference, payload)
    except InvalidReferenceError as exc:
        raise HTTPException(status_code=404, detail="Unknown request reference") from exc
    except AlreadyResolvedError as exc:
        raise HTTPException(status_code=409, detail="Request is already resolved") from exc
