from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .session_database import get_session
from .user_models import User

router = APIRouter(
    prefix="/session/users",
    tags=["users"]
)

# 1. 전체 사용자 조회
@router.get("/")
def get_all_users(db: Session = Depends(get_session)):
    try:
        users = db.query(User).all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return users