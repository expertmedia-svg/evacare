from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import oauth2_scheme
from app.models.models import Payment
from sqlalchemy import func

router = APIRouter()

@router.get("/methods/summary")
def payment_methods_summary(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    result = db.query(Payment.method, func.sum(Payment.amount), func.count(Payment.id)).group_by(Payment.method).all()
    return [{"method": m, "total": t, "count": c} for m, t, c in result]

@router.get("/")
def list_payments(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    payments = db.query(Payment).order_by(Payment.created_at.desc()).limit(100).all()
    return [{"id": p.id, "sale_id": p.sale_id, "method": p.method, "amount": p.amount, "created_at": str(p.created_at)} for p in payments]
