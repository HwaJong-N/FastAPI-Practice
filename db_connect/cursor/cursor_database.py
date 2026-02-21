import pymysql
import logging
import time

from dbutils.pooled_db import PooledDB
from starlette.config import Config

config = Config(".env")

# Connection Pool 설정 (Spring의 HikariCP 역할)
# pymysql은 자체 풀 기능이 없으므로, 보통 dbutils 라이브러리의 PooledDB를 함께 사용
POOL = PooledDB(
    creator=pymysql,
    host=config('DB_HOST'),
    user=config('DB_USER'),
    password=config('DB_PASSWORD'),
    database=config('DB_DATABASE'),
    cursorclass=pymysql.cursors.DictCursor, # 결과를 딕셔너리로 반환
    autocommit=False,
    mincached=5,       # 시작할 때 5개는 미리 연결해둬라 (Warm-up)
    maxcached=10,      # 사용 안 할 때도 최대 10개까지는 풀에 보관해라
    maxconnections=10, # 어떤 경우에도 전체 연결은 10개를 넘기지 마라
    blocking=True,     # 10개가 다 차면 에러 대신 기다리게 해라
)

def check_pool_status(header_text: str, connection=None, waiting_time=None):
    active = POOL._connections
    idle = len(POOL._idle_cache)
    if connection and waiting_time:
        logging.info(f"[{header_text}] Waiting Time: {waiting_time:.2f}s, Pool Stats: active={active}, idle={idle}, connection={connection}")
    elif connection and waiting_time is None:
        logging.info(f"[{header_text}] Pool Stats: active={active}, idle={idle}, connection={connection}")
    else:
        logging.info(f"[{header_text}] Pool Stats: active={active}, idle={idle}")

def get_db_conn():
    logging.info("[cursor] get_db_connection")
    start = time.time()
    #logging.info(f"POOL Internal Vars: {vars(POOL)}") # 출력 가능한 정보 확인

    # 1. 커넥션 가져오기 전 상태 체크
    # check_pool_status("Before Get Connection")

    conn = POOL.connection()
    elapsed = time.time() - start

    # 2. 커넥션 가져온 후 상태 체크
    check_pool_status("After Get Connection", conn, elapsed)

    try:
        yield conn
    finally:
        # 3. 커넥션 반납 전
        check_pool_status("Before Close Connection", conn)

        logging.info("[cursor] db_connection_close ( pool return )")
        conn.close() # 실제 종료가 아니라 풀에 반납됨

        # 4. 커넥션 반납 후
        check_pool_status("After Close Connection")