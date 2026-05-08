from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import random, string
from app.core.database import get_db
from app.core.security import oauth2_scheme
from app.models.models import Order, OrderItem, Product, OrderStatus

router = APIRouter()

class OrderItemIn(BaseModel):
    product_id: int
    quantity: int

class OrderCreate(BaseModel):
    customer_id: Optional[int] = None
    items: List[OrderItemIn]
    delivery_address: Optional[str] = None
    customer_phone: Optional[str] = None
    notes: Optional[str] = None

def gen_order_number():
    return "CMD" + datetime.now().strftime("%Y%m%d") + "".join(random.choices(string.digits, k=3))

@router.post("/")
def create_order(data: OrderCreate, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    total = 0
    items = []
    for item in data.items:
        p = db.query(Product).filter(Product.id == item.product_id).first()
        if not p:
            raise HTTPException(404, f"Produit {item.product_id} introuvable")
        subtotal = p.selling_price * item.quantity
        total += subtotal
        items.append((p, item.quantity, p.selling_price, subtotal))
    order = Order(
        customer_id=data.customer_id, total_amount=total,
        delivery_address=data.delivery_address, customer_phone=data.customer_phone,
        notes=data.notes, order_number=gen_order_number()
    )
    db.add(order)
    db.flush()
    for p, qty, price, sub in items:
        oi = OrderItem(order_id=order.id, product_id=p.id, quantity=qty, unit_price=price, subtotal=sub)
        db.add(oi)
    db.commit()
    db.refresh(order)
    return {"id": order.id, "order_number": order.order_number, "total": order.total_amount, "status": order.status}

@router.get("/")
def list_orders(status: Optional[str] = None, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    q = db.query(Order)
    if status:
        q = q.filter(Order.status == status)
    orders = q.order_by(Order.created_at.desc()).limit(100).all()
    return [{"id": o.id, "order_number": o.order_number, "customer": o.customer.full_name if o.customer else "Anonyme", "total": o.total_amount, "status": o.status, "created_at": str(o.created_at)} for o in orders]

@router.put("/{order_id}/status")
def update_order_status(order_id: int, status: str, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(404, "Commande introuvable")
    o.status = status
    db.commit()
    return {"message": f"Statut mis à jour: {status}"}
