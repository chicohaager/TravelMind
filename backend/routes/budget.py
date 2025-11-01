"""
Budget/Expenses Router
Track trip expenses with participant cost splitting using SQLite
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Optional, Any, Union
from datetime import datetime, date
from enum import Enum
from models.database import get_db
from models.expense import Expense
from models.participant import Participant

router = APIRouter()


class ExpenseCategory(str, Enum):
    FOOD = "food"
    TRANSPORT = "transport"
    ACCOMMODATION = "accommodation"
    ACTIVITIES = "activities"
    SHOPPING = "shopping"
    OTHER = "other"


class ParticipantSplit(BaseModel):
    """How an expense is split for one participant"""
    participant_id: int
    amount: float

    model_config = ConfigDict(from_attributes=True)


class ExpenseCreate(BaseModel):
    title: str
    amount: float
    currency: str = "EUR"
    category: str = "other"
    date: date
    paid_by: int
    notes: Optional[str] = None
    receipt_url: Optional[str] = None
    splits: List[dict] = []  # Simple list of dicts instead of ParticipantSplit

    model_config = ConfigDict(from_attributes=True)


class ExpenseUpdate(BaseModel):
    title: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    category: Optional[str] = None
    date: Optional[Any] = None  # Accept any type and validate manually
    paid_by: Optional[int] = None
    notes: Optional[str] = None
    receipt_url: Optional[str] = None
    splits: Optional[List[dict]] = None  # Simple list of dicts

    @field_validator('date', mode='before')
    @classmethod
    def parse_date(cls, v):
        if v is None:
            return None
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            try:
                return datetime.strptime(v, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError('Invalid date format. Use YYYY-MM-DD')
        raise ValueError(f'Invalid date type: {type(v)}')


class ParticipantBalance(BaseModel):
    """Balance information for a participant"""
    name: str
    paid: float
    owes: float
    balance: float

    model_config = ConfigDict(from_attributes=True)


class BudgetSummary(BaseModel):
    """Budget summary for a trip"""
    total_expenses: float
    by_category: dict[str, float]
    by_participant: dict[str, Any]  # Using Any to avoid recursion
    currency: str

    model_config = ConfigDict(from_attributes=True)


@router.get("/{trip_id}/expenses")
async def get_expenses(trip_id: int, db: AsyncSession = Depends(get_db)):
    """Get all expenses for a trip"""
    # Get expenses
    result = await db.execute(
        select(Expense)
        .where(Expense.trip_id == trip_id)
        .order_by(Expense.date.desc())
    )
    expenses = result.scalars().all()

    # Get participants for name enrichment
    participants_result = await db.execute(
        select(Participant).where(Participant.trip_id == trip_id)
    )
    participants = {p.id: p.name for p in participants_result.scalars().all()}

    # Enrich with participant names
    enriched = []
    for expense in expenses:
        enriched.append({
            "id": expense.id,
            "trip_id": expense.trip_id,
            "title": expense.title,
            "amount": expense.amount,
            "currency": expense.currency,
            "category": expense.category,
            "date": expense.date.isoformat(),
            "paid_by": expense.paid_by,
            "paid_by_name": participants.get(expense.paid_by, "Unbekannt"),
            "notes": expense.notes,
            "receipt_url": expense.receipt_url,
            "splits": expense.splits,
            "created_at": expense.created_at.isoformat() if expense.created_at else None
        })

    return enriched


# Handler function for creating expenses
async def _create_expense_handler(
    trip_id: int,
    expense: ExpenseCreate,
    db: AsyncSession
):
    """Create a new expense"""
    # Get participants for validation
    participants_result = await db.execute(
        select(Participant).where(Participant.trip_id == trip_id)
    )
    participants = {p.id: p.name for p in participants_result.scalars().all()}

    # Validate paid_by participant exists
    if expense.paid_by not in participants:
        raise HTTPException(status_code=404, detail="Participant who paid not found")

    # Validate all split participants exist
    for split in expense.splits:
        if split.get("participant_id") not in participants:
            raise HTTPException(
                status_code=404,
                detail=f"Participant {split.get('participant_id')} not found"
            )

    # Validate splits sum to total amount (with small tolerance for rounding)
    total_split = sum(split.get("amount", 0) for split in expense.splits)
    if abs(total_split - expense.amount) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Splits total ({total_split}) must equal expense amount ({expense.amount})"
        )

    new_expense = Expense(
        trip_id=trip_id,
        title=expense.title,
        amount=expense.amount,
        currency=expense.currency,
        category=expense.category,
        date=expense.date,
        paid_by=expense.paid_by,
        notes=expense.notes,
        receipt_url=expense.receipt_url,
        splits=expense.splits
    )

    db.add(new_expense)
    await db.commit()
    await db.refresh(new_expense)

    # Return with participant name
    return {
        "id": new_expense.id,
        "trip_id": new_expense.trip_id,
        "title": new_expense.title,
        "amount": new_expense.amount,
        "currency": new_expense.currency,
        "category": new_expense.category,
        "date": new_expense.date.isoformat(),
        "paid_by": new_expense.paid_by,
        "paid_by_name": participants.get(new_expense.paid_by, "Unbekannt"),
        "notes": new_expense.notes,
        "receipt_url": new_expense.receipt_url,
        "splits": new_expense.splits,
        "created_at": new_expense.created_at.isoformat() if new_expense.created_at else None
    }

@router.post("/{trip_id}/expenses", status_code=201)
async def create_expense(
    trip_id: int,
    expense: ExpenseCreate,
    db: AsyncSession = Depends(get_db)
):
    return await _create_expense_handler(trip_id, expense, db)

@router.post("/{trip_id}/expenses/", status_code=201)
async def create_expense_slash(
    trip_id: int,
    expense: ExpenseCreate,
    db: AsyncSession = Depends(get_db)
):
    return await _create_expense_handler(trip_id, expense, db)


@router.put("/expenses/{expense_id}")
async def update_expense(
    expense_id: int,
    expense: ExpenseUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an expense"""
    result = await db.execute(select(Expense).where(Expense.id == expense_id))
    existing_expense = result.scalar_one_or_none()

    if not existing_expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    # If splits are being updated, validate them
    if expense.splits is not None:
        # Get participants
        participants_result = await db.execute(
            select(Participant).where(Participant.trip_id == existing_expense.trip_id)
        )
        participants = {p.id: p for p in participants_result.scalars().all()}

        for split in expense.splits:
            if split.get("participant_id") not in participants:
                raise HTTPException(
                    status_code=404,
                    detail=f"Participant {split.get('participant_id')} not found"
                )

        # Validate splits sum
        amount = expense.amount if expense.amount is not None else existing_expense.amount
        total_split = sum(split.get("amount", 0) for split in expense.splits)
        if abs(total_split - amount) > 0.01:
            raise HTTPException(
                status_code=400,
                detail=f"Splits total ({total_split}) must equal expense amount ({amount})"
            )

    # Update fields
    update_data = expense.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(existing_expense, field, value)

    await db.commit()
    await db.refresh(existing_expense)

    # Get participant name
    participants_result = await db.execute(
        select(Participant).where(Participant.trip_id == existing_expense.trip_id)
    )
    participants = {p.id: p.name for p in participants_result.scalars().all()}

    return {
        "id": existing_expense.id,
        "trip_id": existing_expense.trip_id,
        "title": existing_expense.title,
        "amount": existing_expense.amount,
        "currency": existing_expense.currency,
        "category": existing_expense.category,
        "date": existing_expense.date.isoformat(),
        "paid_by": existing_expense.paid_by,
        "paid_by_name": participants.get(existing_expense.paid_by, "Unbekannt"),
        "notes": existing_expense.notes,
        "receipt_url": existing_expense.receipt_url,
        "splits": existing_expense.splits,
        "created_at": existing_expense.created_at.isoformat() if existing_expense.created_at else None
    }


@router.delete("/expenses/{expense_id}", status_code=204)
async def delete_expense(expense_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an expense"""
    result = await db.execute(select(Expense).where(Expense.id == expense_id))
    expense = result.scalar_one_or_none()

    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    await db.delete(expense)
    await db.commit()

    return None


@router.get("/{trip_id}/budget-summary", response_model=BudgetSummary)
async def get_budget_summary(trip_id: int, db: AsyncSession = Depends(get_db)):
    """Get budget summary with totals and balances"""
    # Get expenses
    expenses_result = await db.execute(
        select(Expense).where(Expense.trip_id == trip_id)
    )
    expenses = expenses_result.scalars().all()

    # Get participants
    participants_result = await db.execute(
        select(Participant).where(Participant.trip_id == trip_id)
    )
    participants = {p.id: p.name for p in participants_result.scalars().all()}

    # Calculate totals
    total = sum(e.amount for e in expenses)
    currency = expenses[0].currency if expenses else "EUR"

    # By category
    by_category = {}
    for exp in expenses:
        category = exp.category
        by_category[category] = by_category.get(category, 0) + exp.amount

    # By participant
    by_participant = {}
    for pid, name in participants.items():
        by_participant[str(pid)] = {
            "name": name,
            "paid": 0.0,
            "owes": 0.0,
            "balance": 0.0
        }

    # Calculate paid amounts
    for exp in expenses:
        pid_str = str(exp.paid_by)
        if pid_str in by_participant:
            by_participant[pid_str]["paid"] += exp.amount

    # Calculate owed amounts from splits
    for exp in expenses:
        for split in exp.splits:
            pid_str = str(split.get("participant_id"))
            if pid_str in by_participant:
                by_participant[pid_str]["owes"] += split.get("amount", 0)

    # Calculate balances
    for pid_str in by_participant:
        participant_data = by_participant[pid_str]
        participant_data["balance"] = participant_data["paid"] - participant_data["owes"]

    return {
        "total_expenses": total,
        "by_category": by_category,
        "by_participant": by_participant,
        "currency": currency
    }


@router.post("/{trip_id}/expenses/split-equally", status_code=201)
async def split_expense_equally(
    trip_id: int,
    title: str,
    amount: float,
    category: str,
    paid_by: int,
    date: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Create an expense split equally among all participants

    Helper endpoint for quick expense entry
    """
    # Get participants
    participants_result = await db.execute(
        select(Participant).where(Participant.trip_id == trip_id)
    )
    participants = list(participants_result.scalars().all())

    if not participants:
        raise HTTPException(status_code=400, detail="No participants found for this trip")

    # Validate paid_by
    if paid_by not in [p.id for p in participants]:
        raise HTTPException(status_code=404, detail="Participant who paid not found")

    # Calculate equal split
    per_person = amount / len(participants)
    splits = [{"participant_id": p.id, "amount": per_person} for p in participants]

    # Create expense
    expense_date = datetime.fromisoformat(date).date() if date else datetime.now().date()

    new_expense = Expense(
        trip_id=trip_id,
        title=title,
        amount=amount,
        currency="EUR",
        category=category,
        date=expense_date,
        paid_by=paid_by,
        splits=splits
    )

    db.add(new_expense)
    await db.commit()
    await db.refresh(new_expense)

    # Get participant names
    participants_dict = {p.id: p.name for p in participants}

    return {
        "id": new_expense.id,
        "trip_id": new_expense.trip_id,
        "title": new_expense.title,
        "amount": new_expense.amount,
        "currency": new_expense.currency,
        "category": new_expense.category,
        "date": new_expense.date.isoformat(),
        "paid_by": new_expense.paid_by,
        "paid_by_name": participants_dict.get(new_expense.paid_by, "Unbekannt"),
        "notes": new_expense.notes,
        "receipt_url": new_expense.receipt_url,
        "splits": new_expense.splits,
        "created_at": new_expense.created_at.isoformat() if new_expense.created_at else None
    }
