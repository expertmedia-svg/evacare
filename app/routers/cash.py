from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from app.core.database import get_db
from app.core.security import oauth2_scheme, SECRET_KEY, ALGORITHM
from app.models.models import CashJournal, CashType
from jose import jwt

router = APIRouter()

class CashEntryIn(BaseModel):
    entry_type: CashType
    amount: float
    description: Optional[str] = None
    reference: Optional[str] = None

@router.post("/entry")
def add_cash_entry(data: CashEntryIn, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    last = db.query(CashJournal).order_by(CashJournal.id.desc()).first()
    balance_before = last.balance_after if last else 0
    if data.entry_type == CashType.entry:
        balance_after = balance_before + data.amount
    else:
        balance_after = balance_before - data.amount
    entry = CashJournal(
        entry_type=data.entry_type, amount=data.amount,
        description=data.description, reference=data.reference,
        user_id=payload.get("user_id"), balance_after=balance_after
    )
    db.add(entry)
    db.commit()
    return {"message": "Entrée caisse enregistrée", "balance": balance_after}

@router.get("/balance")
def get_balance(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    last = db.query(CashJournal).order_by(CashJournal.id.desc()).first()
    return {"balance": last.balance_after if last else 0}

@router.get("/history")
def cash_history(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    entries = db.query(CashJournal).order_by(CashJournal.created_at.desc()).limit(100).all()
    return [{"id": e.id, "type": e.entry_type, "amount": e.amount, "description": e.description, "balance_after": e.balance_after, "created_at": str(e.created_at)} for e in entries]

@router.get("/today")
def today_cash(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    from datetime import date as d
    today = d.today()
    entries = db.query(CashJournal).filter(CashJournal.created_at >= today).all()
    income = sum(e.amount for e in entries if e.entry_type == CashType.entry)
    outcome = sum(e.amount for e in entries if e.entry_type != CashType.entry)
    return {"today": str(today), "income": income, "outcome": outcome, "net": income - outcome}
