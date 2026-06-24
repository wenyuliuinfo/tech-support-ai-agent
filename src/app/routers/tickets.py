"""Tickets endpoint — account-scoped ticket retrieval."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from services.auth import get_account_id_from_request
from services.ticket_service import TicketService

router = APIRouter(tags=["tickets"])


class TicketResponse(BaseModel):
    ticket_number: str
    account_id: str
    subject: str
    status: str
    created_at: str
    resolution: str | None = None


class TicketsResponse(BaseModel):
    tickets: list[TicketResponse]


ticket_service = TicketService()


@router.get("/tickets", response_model=TicketsResponse)
async def get_tickets(
    request: Request,
    account_id: UUID = Depends(get_account_id_from_request),
) -> TicketsResponse:
    records = await ticket_service.get_tickets_for_account(account_id)
    return TicketsResponse(
        tickets=[
            TicketResponse(
                ticket_number=r.ticket_number,
                account_id=str(r.account_id),
                subject=r.subject,
                status=r.status,
                created_at=r.created_at,
                resolution=r.resolution,
            )
            for r in records
        ]
    )
