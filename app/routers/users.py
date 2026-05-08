from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from app.core.database import get_db
from app.core.security import oauth2_scheme, get_password_hash
from app.models.models import User, UserRole

router = APIRouter()

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

@router.get("/")
def list_users(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    users = db.query(User).all()
    return [{"id": u.id, "full_name": u.full_name, "email": u.email, "phone": u.phone, "role": u.role, "is_active": u.is_active} for u in users]

@router.put("/{user_id}")
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, "Utilisateur introuvable")
    for k, v in data.dict(exclude_none=True).items():
        setattr(u, k, v)
    db.commit()
    return {"message": "Utilisateur mis à jour"}

@router.post("/{user_id}/reset-password")
def reset_password(user_id: int, new_password: str, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, "Utilisateur introuvable")
    u.hashed_password = get_password_hash(new_password)
    db.commit()
    return {"message": "Mot de passe réinitialisé"}
