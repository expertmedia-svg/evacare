from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import random, string
from app.core.database import get_db
from app.core.security import oauth2_scheme, SECRET_KEY, ALGORITHM
from app.models.models import Sale, SaleItem, Product, Customer, Payment, CashJournal, CashType, StockMovement, StockMovementType
from jose import jwt

router = APIRouter()

class SaleItemIn(BaseModel):
    product_id: int
    quantity: int
    unit_price: Optional[float] = None

class SaleCreate(BaseModel):
    customer_id: Optional[int] = None
    items: List[SaleItemIn]
    payment_method: str = "cash"
    amount_paid: Optional[float] = None
    discount: float = 0
    notes: Optional[str] = None

def generate_receipt():
    return "RC" + datetime.now().strftime("%Y%m%d") + "".join(random.choices(string.digits, k=4))

@router.post("/")
def create_sale(data: SaleCreate, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    seller_id = payload.get("user_id")
    total = 0
    total_cost = 0
    sale_items = []
    for item in data.items:
        p = db.query(Product).filter(Product.id == item.product_id).first()
        if not p:
            raise HTTPException(404, f"Produit {item.product_id} introuvable")
        if p.stock_quantity < item.quantity:
            raise HTTPException(400, f"Stock insuffisant pour {p.name}: {p.stock_quantity} disponible")
        price = item.unit_price or p.selling_price
        subtotal = price * item.quantity
        total += subtotal
        total_cost += p.purchase_price * item.quantity
        sale_items.append((p, item.quantity, price, subtotal, p.purchase_price))
    total_after_discount = total - data.discount
    amount_paid = data.amount_paid if data.amount_paid is not None else total_after_discount
    credit = max(0, total_after_discount - amount_paid)
    sale = Sale(
        customer_id=data.customer_id, seller_id=seller_id,
        total_amount=total_after_discount, total_cost=total_cost,
        discount=data.discount, payment_method=data.payment_method,
        amount_paid=amount_paid, credit_amount=credit,
        notes=data.notes, receipt_number=generate_receipt()
    )
    db.add(sale)
    db.flush()
    for p, qty, price, subtotal, cost in sale_items:
        si = SaleItem(sale_id=sale.id, product_id=p.id, quantity=qty, unit_price=price, unit_cost=cost, subtotal=subtotal)
        db.add(si)
        p.stock_quantity -= qty
        if p.stock_quantity == 0:
            from app.models.models import ProductStatus
            p.status = ProductStatus.rupture
        mov = StockMovement(product_id=p.id, movement_type=StockMovementType.exit, quantity=qty, reason=f"Vente #{sale.receipt_number}")
        db.add(mov)
    pmt = Payment(sale_id=sale.id, method=data.payment_method, amount=amount_paid)
    db.add(pmt)
    if data.customer_id and credit > 0:
        customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
        if customer:
            customer.credit_balance += credit
    cash_entry = CashJournal(entry_type=CashType.entry, amount=amount_paid, description=f"Vente {sale.receipt_number}", user_id=seller_id)
    db.add(cash_entry)
    db.commit()
    db.refresh(sale)
    return {
        "id": sale.id, "receipt_number": sale.receipt_number,
        "total_amount": sale.total_amount, "amount_paid": sale.amount_paid,
        "credit_amount": sale.credit_amount, "profit": sale.profit,
        "message": "Vente enregistrée avec succès"
    }

@router.get("/")
def list_sales(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    sales = db.query(Sale).order_by(Sale.created_at.desc()).offset(skip).limit(limit).all()
    result = []
    for s in sales:
        result.append({
            "id": s.id, "receipt_number": s.receipt_number,
            "customer_name": s.customer.full_name if s.customer else "Client anonyme",
            "total_amount": s.total_amount, "profit": s.profit,
            "payment_method": s.payment_method, "amount_paid": s.amount_paid,
            "credit_amount": s.credit_amount,
            "items_count": len(s.items),
            "created_at": str(s.created_at)
        })
    return result

@router.get("/{sale_id}")
def get_sale(sale_id: int, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    s = db.query(Sale).filter(Sale.id == sale_id).first()
    if not s:
        raise HTTPException(404, "Vente introuvable")
    return {
        "id": s.id, "receipt_number": s.receipt_number,
        "customer": {"id": s.customer.id, "name": s.customer.full_name} if s.customer else None,
        "seller": s.seller.full_name if s.seller else None,
        "total_amount": s.total_amount, "total_cost": s.total_cost,
        "discount": s.discount, "profit": s.profit,
        "payment_method": s.payment_method, "amount_paid": s.amount_paid,
        "credit_amount": s.credit_amount, "notes": s.notes,
        "created_at": str(s.created_at),
        "items": [{"product_name": i.product.name, "quantity": i.quantity, "unit_price": i.unit_price, "subtotal": i.subtotal} for i in s.items]
    }

@router.get("/today/summary")
def today_summary(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    from datetime import date
    today = date.today()
    sales = db.query(Sale).filter(Sale.created_at >= today).all()
    total_revenue = sum(s.total_amount for s in sales)
    total_profit = sum(s.profit for s in sales)
    return {"date": str(today), "sales_count": len(sales), "total_revenue": total_revenue, "total_profit": total_profit}
