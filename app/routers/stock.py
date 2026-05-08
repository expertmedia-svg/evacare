from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from app.core.database import get_db
from app.core.security import oauth2_scheme, SECRET_KEY, ALGORITHM
from app.models.models import StockMovement, StockMovementType, Product, ProductStatus
from jose import jwt
from datetime import date

router = APIRouter()

class StockIn(BaseModel):
    product_id: int
    movement_type: StockMovementType
    quantity: int
    reason: Optional[str] = None
    reference: Optional[str] = None
    unit_cost: Optional[float] = None

class StockOut(BaseModel):
    id: int
    product_id: int
    movement_type: str
    quantity: int
    reason: Optional[str]
    reference: Optional[str]
    unit_cost: Optional[float]
    created_at: str
    class Config:
        from_attributes = True

@router.get("/movements")
def get_movements(product_id: Optional[int] = None, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    q = db.query(StockMovement)
    if product_id:
        q = q.filter(StockMovement.product_id == product_id)
    movements = q.order_by(StockMovement.created_at.desc()).limit(200).all()
    result = []
    for m in movements:
        result.append({
            "id": m.id, "product_id": m.product_id,
            "product_name": m.product.name if m.product else "",
            "movement_type": m.movement_type, "quantity": m.quantity,
            "reason": m.reason, "unit_cost": m.unit_cost,
            "created_at": str(m.created_at)
        })
    return result

@router.post("/add")
def add_stock(data: StockIn, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    p = db.query(Product).filter(Product.id == data.product_id).first()
    if not p:
        raise HTTPException(404, "Produit introuvable")
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    mov = StockMovement(
        product_id=data.product_id, movement_type=data.movement_type,
        quantity=data.quantity, reason=data.reason,
        reference=data.reference, unit_cost=data.unit_cost,
        user_id=payload.get("user_id")
    )
    if data.movement_type == StockMovementType.entry:
        p.stock_quantity += data.quantity
    elif data.movement_type in [StockMovementType.exit, StockMovementType.loss]:
        if p.stock_quantity < data.quantity:
            raise HTTPException(400, "Stock insuffisant")
        p.stock_quantity -= data.quantity
    elif data.movement_type == StockMovementType.adjustment:
        p.stock_quantity = data.quantity
    if p.stock_quantity == 0:
        p.status = ProductStatus.rupture
    elif p.status == ProductStatus.rupture:
        p.status = ProductStatus.available
    db.add(mov)
    db.commit()
    return {"message": "Mouvement enregistré", "new_stock": p.stock_quantity}

@router.get("/expiring-soon")
def expiring_soon(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    from datetime import timedelta, date as d
    limit = d.today() + timedelta(days=30)
    products = db.query(Product).filter(
        Product.expiry_date != None,
        Product.expiry_date <= limit,
        Product.is_active == True
    ).all()
    return [{"id": p.id, "name": p.name, "expiry_date": str(p.expiry_date), "stock": p.stock_quantity} for p in products]

@router.get("/value")
def stock_value(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    products = db.query(Product).filter(Product.is_active == True).all()
    total_cost = sum(p.purchase_price * p.stock_quantity for p in products)
    total_retail = sum(p.selling_price * p.stock_quantity for p in products)
    return {"total_cost_value": total_cost, "total_retail_value": total_retail, "product_count": len(products)}
