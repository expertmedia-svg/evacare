from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
import os, shutil, uuid
from app.core.database import get_db
from app.core.security import oauth2_scheme
from app.models.models import Product, ProductStatus, StockMovement, StockMovementType
from jose import jwt
from app.core.security import SECRET_KEY, ALGORITHM

router = APIRouter()

class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category_id: Optional[int] = None
    purchase_price: float
    selling_price: float
    stock_quantity: int = 0
    low_stock_threshold: int = 5
    supplier: Optional[str] = None
    entry_date: Optional[date] = None
    expiry_date: Optional[date] = None
    usage_instructions: Optional[str] = None
    status: ProductStatus = ProductStatus.available

class ProductOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    category_id: Optional[int]
    purchase_price: float
    selling_price: float
    stock_quantity: int
    low_stock_threshold: int
    supplier: Optional[str]
    entry_date: Optional[date]
    expiry_date: Optional[date]
    image: Optional[str]
    status: str
    usage_instructions: Optional[str]
    margin_percent: float
    is_active: bool
    class Config:
        from_attributes = True

def get_user_id(token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return payload.get("user_id")

@router.get("/", response_model=List[ProductOut])
def list_products(
    category_id: Optional[int] = None,
    status: Optional[str] = None,
    low_stock: bool = False,
    search: Optional[str] = None,
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    q = db.query(Product).filter(Product.is_active == True)
    if category_id:
        q = q.filter(Product.category_id == category_id)
    if status:
        q = q.filter(Product.status == status)
    if low_stock:
        q = q.filter(Product.stock_quantity <= Product.low_stock_threshold)
    if search:
        q = q.filter(Product.name.ilike(f"%{search}%"))
    return q.offset(skip).limit(limit).all()

@router.post("/", response_model=ProductOut)
def create_product(product: ProductCreate, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    p = Product(**product.dict())
    db.add(p)
    db.commit()
    db.refresh(p)
    if p.stock_quantity > 0:
        mov = StockMovement(
            product_id=p.id, movement_type=StockMovementType.entry,
            quantity=p.stock_quantity, reason="Stock initial"
        )
        db.add(mov)
        db.commit()
    return p

@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    return p

@router.put("/{product_id}", response_model=ProductOut)
def update_product(product_id: int, product: ProductCreate, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    for k, v in product.dict().items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p

@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    p.is_active = False
    p.status = ProductStatus.disabled
    db.commit()
    return {"message": "Produit désactivé"}

@router.post("/{product_id}/upload-image")
def upload_image(product_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    ext = file.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    path = f"uploads/{filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    p.image = f"/uploads/{filename}"
    db.commit()
    return {"image": p.image}

@router.get("/alerts/low-stock")
def low_stock_alerts(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    products = db.query(Product).filter(
        Product.is_active == True,
        Product.stock_quantity <= Product.low_stock_threshold
    ).all()
    return [{"id": p.id, "name": p.name, "stock": p.stock_quantity, "threshold": p.low_stock_threshold, "status": p.status} for p in products]
