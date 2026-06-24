"""PostgreSQL ticket and account repository."""

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from config import get_settings


@dataclass(frozen=True)
class TicketRecord:
    ticket_number: str
    account_id: UUID
    subject: str
    status: str
    created_at: str
    resolution: str | None


class TicketRepository:
    def __init__(self) -> None:
        settings = get_settings()
        self._engine: AsyncEngine = create_async_engine(
            settings.database_url,
            echo=False,
        )

    async def ensure_account(self, account_id: UUID) -> None:
        async with AsyncSession(self._engine) as session:
            await session.execute(
                text(
                    "INSERT INTO accounts (account_id, email, name) "
                    "VALUES (:account_id, :email, :name) "
                    "ON CONFLICT (account_id) DO NOTHING"
                ),
                {
                    "account_id": account_id,
                    "email": f"{account_id}@placeholder.local",
                    "name": str(account_id)[:8],
                },
            )
            await session.commit()

    async def create_ticket(
        self,
        account_id: UUID,
        subject: str,
        resolution: str | None = None,
    ) -> TicketRecord:
        ticket_number = f"TKT-{secrets.token_hex(4).upper()}"
        now = datetime.now(UTC).replace(tzinfo=None)

        async with AsyncSession(self._engine) as session:
            await session.execute(
                text(
                    "INSERT INTO tickets "
                    "(ticket_number, account_id, subject, status, created_at, resolution) "
                    "VALUES (:ticket_number, :account_id, :subject, :status, :created_at, :resolution)"
                ),
                {
                    "ticket_number": ticket_number,
                    "account_id": account_id,
                    "subject": subject[:255],
                    "status": "closed" if resolution else "open",
                    "created_at": now,
                    "resolution": resolution,
                },
            )
            await session.commit()

        return TicketRecord(
            ticket_number=ticket_number,
            account_id=account_id,
            subject=subject[:255],
            status="closed" if resolution else "open",
            created_at=now.isoformat(),
            resolution=resolution,
        )

    async def get_tickets_for_account(
        self, account_id: UUID
    ) -> list[TicketRecord]:
        async with AsyncSession(self._engine) as session:
            result = await session.execute(
                text(
                    "SELECT ticket_number, account_id, subject, status, "
                    "created_at, resolution FROM tickets "
                    "WHERE account_id = :account_id "
                    "ORDER BY created_at DESC"
                ),
                {"account_id": account_id},
            )
            rows = result.fetchall()
            return [
                TicketRecord(
                    ticket_number=row[0],
                    account_id=row[1],
                    subject=row[2],
                    status=row[3],
                    created_at=str(row[4]),
                    resolution=row[5],
                )
                for row in rows
            ]

    async def search_tickets_for_account(
        self, account_id: UUID, query: str, limit: int = 5
    ) -> list[TicketRecord]:
        async with AsyncSession(self._engine) as session:
            result = await session.execute(
                text(
                    "SELECT ticket_number, account_id, subject, status, "
                    "created_at, resolution FROM tickets "
                    "WHERE account_id = :account_id "
                    "AND (subject ILIKE :pattern OR resolution ILIKE :pattern) "
                    "ORDER BY created_at DESC "
                    "LIMIT :limit"
                ),
                {
                    "account_id": account_id,
                    "pattern": f"%{query}%",
                    "limit": limit,
                },
            )
            rows = result.fetchall()
            return [
                TicketRecord(
                    ticket_number=row[0],
                    account_id=row[1],
                    subject=row[2],
                    status=row[3],
                    created_at=str(row[4]),
                    resolution=row[5],
                )
                for row in rows
            ]
