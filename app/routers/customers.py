from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from app.core.database import get_db
from app.core.security import oauth2_scheme
from app.models.models import Customer

router = APIRouter()

class CustomerCreate(BaseModel):
    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    notes: Optional[str] = None

class CustomerOut(BaseModel):
    id: int
    full_name: str
    phone: Optional[str]
    email: Optional[str]
    address: Optional[str]
    city: Optional[str]
    loyalty_points: int
    credit_balance: float
    is_active: bool
    class Config:
        from_attributes = True

@router.get("/", response_model=List[CustomerOut])
def list_customers(search: Optional[str] = None, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    q = db.query(Customer).filter(Customer.is_active == True)
    if search:
        q = q.filter(Customer.full_name.ilike(f"%{search}%") | Customer.phone.ilike(f"%{search}%"))
    return q.all()

@router.post("/", response_model=CustomerOut)
def create_customer(data: CustomerCreate, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    if data.phone:
        existing = db.query(Customer).filter(Customer.phone == data.phone).first()
        if existing:
            raise HTTPException(400, "Numéro de téléphone déjà utilisé")
    c = Customer(**data.dict())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

@router.get("/{customer_id}")
def get_customer(customer_id: int, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(404, "Client introuvable")
    return {
        "id": c.id, "full_name": c.full_name, "phone": c.phone,
        "email": c.email, "address": c.address, "city": c.city,
        "loyalty_points": c.loyalty_points, "credit_balance": c.credit_balance,
        "sales_count": len(c.sales),
        "total_spent": sum(s.total_amount for s in c.sales),
        "created_at": str(c.created_at)
    }

@router.put("/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: int, data: CustomerCreate, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(404, "Client introuvable")
    for k, v in data.dict().items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return c

@router.get("/{customer_id}/history")
def customer_history(customer_id: int, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(404, "Client introuvable")
    return [{"id": s.id, "receipt": s.receipt_number, "total": s.total_amount, "date": str(s.created_at)} for s in c.sales]
