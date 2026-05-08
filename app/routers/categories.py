from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from app.core.database import get_db
from app.core.security import oauth2_scheme
from app.models.models import Category

router = APIRouter()

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None

class CategoryOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    icon: Optional[str]
    is_active: bool
    class Config:
        from_attributes = True

@router.get("/", response_model=List[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).filter(Category.is_active == True).all()

@router.post("/", response_model=CategoryOut)
def create_category(cat: CategoryCreate, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    c = Category(**cat.dict())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

@router.put("/{cat_id}", response_model=CategoryOut)
def update_category(cat_id: int, cat: CategoryCreate, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    c = db.query(Category).filter(Category.id == cat_id).first()
    if not c:
        raise HTTPException(404, "Catégorie introuvable")
    for k, v in cat.dict().items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return c

@router.delete("/{cat_id}")
def delete_category(cat_id: int, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    c = db.query(Category).filter(Category.id == cat_id).first()
    if not c:
        raise HTTPException(404, "Catégorie introuvable")
    c.is_active = False
    db.commit()
    return {"message": "Catégorie supprimée"}
