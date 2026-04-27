from uuid import UUID
from fastapi import APIRouter, Depends
from asyncpg import Pool

from app.domain.tickets import TicketCreate, TicketResponse
from app.domain.users import UserInDB
from app.services.ticket_service import create_ticket, get_user_tickets
from app.services.auth_service import get_current_user
from app.infrastructure.database import get_pool

router = APIRouter()

@router.post("/", response_model=TicketResponse)
async def submit_ticket(
    ticket_in: TicketCreate,
    current_user: UserInDB = Depends(get_current_user),
    pool: Pool = Depends(get_pool)
):
    return await create_ticket(ticket_in, current_user.id, pool)

@router.get("/", response_model=list[TicketResponse])
async def list_tickets(
    current_user: UserInDB = Depends(get_current_user),
    pool: Pool = Depends(get_pool)
):
    return await get_user_tickets(current_user.id, pool)
