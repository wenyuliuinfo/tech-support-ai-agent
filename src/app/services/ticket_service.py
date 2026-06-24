"""Ticket service: wraps ticket repository for router consumption."""

from uuid import UUID

from repositories.ticket import TicketRecord, TicketRepository


class TicketService:
    def __init__(self) -> None:
        self._repo = TicketRepository()

    async def get_tickets_for_account(self, account_id: UUID) -> list[TicketRecord]:
        return await self._repo.get_tickets_for_account(account_id)
