from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from app.core.database import get_db
from app.core.security import oauth2_scheme, SECRET_KEY, ALGORITHM
from app.models.models import Expense, ExpenseCategory
from jose import jwt

router = APIRouter()

class ExpenseIn(BaseModel):
    category: ExpenseCategory
    amount: float
    description: Optional[str] = None
    supplier: Optional[str] = None
    receipt_ref: Optional[str] = None
    expense_date: Optional[date] = None

@router.post("/")
def create_expense(data: ExpenseIn, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    exp = Expense(**data.dict(), user_id=payload.get("user_id"))
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return {"id": exp.id, "message": "Dépense enregistrée"}

@router.get("/")
def list_expenses(month: Optional[int] = None, year: Optional[int] = None, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    q = db.query(Expense)
    if month:
        q = q.filter(Expense.expense_date != None)
    expenses = q.order_by(Expense.created_at.desc()).limit(200).all()
    return [{"id": e.id, "category": e.category, "amount": e.amount, "description": e.description, "expense_date": str(e.expense_date), "created_at": str(e.created_at)} for e in expenses]

@router.get("/summary")
def expenses_summary(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    from sqlalchemy import func as sqlfunc
    result = db.query(Expense.category, sqlfunc.sum(Expense.amount)).group_by(Expense.category).all()
    return [{"category": cat, "total": total} for cat, total in result]
