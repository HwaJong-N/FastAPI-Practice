import time

from fastapi import APIRouter, Depends, HTTPException
from .cursor_database import get_db_conn  # PooledDB 연결을 빌려오는 함수

router = APIRouter(
    prefix="/cursor/users",
    tags=["users"]
)

# 1. 전체 사용자 조회 (커서 방식)
@router.get("/")
def get_all_users_cursor(conn = Depends(get_db_conn)):
    # TEST 용
    time.sleep(3)
    try:
        cursor = conn.cursor()
        sql = "SELECT id, username, email, full_name, is_active FROM users"
        cursor.execute(sql)
        users = cursor.fetchall()  # DictCursor 설정 덕분에 리스트[딕셔너리]로 반환됨
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
    return users
    