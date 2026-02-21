# DB 를 연결하는 2가지 방식

##  1. Session 방식과 Cursor 방식의 차이

### 1-1. 세션 (Session) 방식 - "객체 중심"

보통 SQLAlchemy 같은 ORM을 쓸 때 사용하는 개념입니다. DB와의 연결을 하나의 '작업 단위(Unit of Work)'로 묶어서 관리합니다.

- 특징: DB 연결을 단순히 여는 게 아니라, 내가 조회한 객체들이 수정됐는지 추적하고 트랜잭션(Commit/Rollback)을 관리하는 관리자 역할을 합니다.

- FastAPI에서의 활용: Depends를 이용해 HTTP 요청이 들어올 때 세션을 만들고, 응답이 나가면 자동으로 닫아주도록 설정합니다.

- 장점: 코드가 파이썬스럽고(Pythonic), 비즈니스 로직에 집중하기 좋습니다.

<br>

### 1-2. 커서 (Cursor) 방식 - "명령 중심"

psycopg2, aiomysql 같은 Low-level 드라이버나 databases 라이브러리를 직접 쓸 때 사용합니다.

- 특징: DB에 SQL 문을 보내고 결과를 한 줄씩 읽어오는 포인터(화살표) 같은 개념입니다.

- 작동 방식: Connection을 먼저 맺고 -> 그 안에서 Cursor를 생성 -> execute("SELECT...") 실행 -> fetchone()이나 fetchall()로 결과 수신.

- 장점: 가볍고 빠릅니다. SQL을 직접 통제하므로 성능 최적화에 유리합니다.


<br><br>

## 2. PooledDB

PooledDB는 **데이터베이스 연결(Connection)을 미리 만들어 두고 빌려주는 창고**이며, Python에서 DBUtils 라이브러리가 제공하는 클래스로, 매번 DB에 접속하고 끊는 비효율을 줄이기 위해 사용합니다.

### 2-1. 커넥션 풀(Connection Pool)이란?

일반적으로 프로그램이 DB에서 데이터를 가져오려면 다음과 같은 과정을 거칩니다.

- DB 서버에 연결 요청 (TCP 핸드쉐이크, 인증 등)

- 연결 생성 (Connection)

- 쿼리 실행 및 결과 수신

- 연결 종료 (Close)

문제는 1번과 2번 과정이 컴퓨터 입장에서 매우 무겁고 시간이 오래 걸리는 작업이라는 점입니다. 사용자가 1,000명 접속하면 이 무거운 과정을 1,000번 반복해야 하는데 PooledDB를 쓰면 이 과정이 바뀝니다.

- 서버가 켜질 때 미리 10개의 연결을 만들어 **풀(Pool)**에 넣어둡니다.

- 요청이 오면 풀에서 노는 연결을 하나 꺼내서 줍니다.

- 작업이 끝나면 연결을 끊지 않고 다시 풀에 반납합니다.

<br>

### 2-2. 왜 PooledDB를 사용해야 하나요?

- 성능 향상 (응답 속도)

매번 연결을 맺고 끊는 오버헤드가 사라지기 때문에 API 응답 속도가 비약적으로 빨라집니다. 특히 FastAPI처럼 비동기로 빠르게 동작하는 프레임워크에서는 DB 연결 병목 현상을 해결하는 핵심 요소입니다.

- DB 서버 자원 보호

DB 서버는 무한정 연결을 받아줄 수 없습니다 (MySQL의 경우 max_connections 제한).

미사용 시: 사용자 500명이 동시에 접속하면 DB 연결도 500개가 생겨 서버가 뻗을 수 있습니다.

PooledDB 사용 시: maxconnections=50으로 설정하면, 접속자가 아무리 많아도 DB 연결은 50개까지만 유지하며 차례대로 처리합니다.

- 안정성 (좀비 커넥션 방지)

네트워크 문제로 연결이 끊기거나, 오래된 연결이 타임아웃되어 에러가 발생하는 상황을 방지합니다. ping 옵션을 통해 "이 연결 아직 살아있니?"를 확인하고 안전한 연결만 꺼내줍니다.

<br>

### 2-3. 주의할 점

- 반드시 ```close()``` 가 필요합니다.

- PooledDB에서 conn.close()는 진짜 연결을 끊는 게 아니라 커넥션 풀에 다시 반환합니다.

- 만약 close()를 안 하면? 창고에서 물건을 꺼내 가기만 하고 반납을 안 하는 꼴이 되어, 결국 커넥션 풀이 비어버리고 서버는 **연결할 자리가 없어요!**라며 멈추게 됩니다. (이를 커넥션 누수라고 합니다.)

<br>

### 2-4. PooledDB 주요 설정 값

- mincached: 풀 생성 시 미리 만들어둘 유휴 커넥션 수

    - 애플리케이션 시작 시 DB와 연결을 미리 맺어둡니다. 0보다 크게 설정하면 첫 요청 시 연결 지연(Latency)이 사라집니다.

- maxcached: 풀에 보관할 최대 유휴 커넥션 수

    - 사용이 끝난 커넥션을 무조건 닫지 않고, 이 숫자만큼은 풀에 살려둡니다. 0이나 None이면 제한이 없습니다.

- maxshared: 공유 가능한 최대 커넥션 수

    - 연결을 '공유 모드'로 요청했을 때 동시에 사용될 수 있는 최대 수입니다. 0이면 공유를 허용하지 않고 각 요청마다 전용 커넥션을 할당합니다.

- maxconnections: 전체 프로세스에서 허용되는 절대적인 최대 커넥션 수

    - DB 서버가 감당할 수 있는 한계를 고려해 설정해야 합니다. 이 수치에 도달하면 blocking 설정에 따라 다음 동작이 결정됩니다.

- blocking: 최대치(maxconnections) 도달 시 대기 여부

    - True: 빈 커넥션이 생길 때까지 스레드를 멈추고 기다립니다.

    - False: 기다리지 않고 즉시 에러(PoolError)를 던집니다.

- maxusage: 커넥션 하나당 최대 재사용 횟수

    - 특정 커넥션이 너무 오래 유지되어 발생할 수 있는 메모리 누수나 고스트 세션을 방지합니다. 설정 횟수에 도달하면 자동으로 연결을 끊고 새로 맺습니다.

- reset: 풀 반납 시 트랜잭션 처리 방식

    - False/None: begin()으로 명시적 시작된 트랜잭션만 롤백합니다.

    - True: 안전을 위해 반납되는 모든 커넥션에 대해 무조건 롤백을 수행합니다.

- ping: 커넥션이 살아있는지 확인하는 시점

    - 0: 확인 안 함.

    - 1: 풀에서 꺼내올 때마다 확인 (가장 안전, 기본값).

    - 2: 커서(cursor())를 생성할 때 확인.

    - 4: 실제 쿼리를 실행할 때 확인.

    - 7: 위 모든 상황(1+2+4)에서 확인.

- failures: 재연결 로직을 적용할 에러 클래스

    - 기본적으로 OperationalError 등이 포함되어 있으며, 특정 커스텀 에러 발생 시에도 재연결을 시도하고 싶을 때 사용합니다.

- setsession: 연결 직후 실행할 SQL 명령 리스트

    - 예: ["SET NAMES utf8mb4", "SET time_zone = '+09:00'"] 같이 세션 초기화가 필요할 때 사용합니다.

- args, kwargs: 기본 DB 드라이버에 전달할 인자

    - pymysql.connect() 등에 들어가는 host, user, password, port 등을 여기에 적습니다.


<br><br>

## 3. PooledDB 테스트 코드

### 3-1. PooledDB 설정

```python
# db_connect/cursor/cursor_database.py

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

...

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
```

<br>

### 3-2. TEST 코드

```python
# test/db_connect/cursor/user_test.py

def test_db_access_by_connection_pool():
    results = []

    def call_api():
        try:
            # 숏커트: 실제 통신이 아닌 로직 테스트를 위해 client 사용
            response = client.get("/cursor/users/")
            results.append(response.status_code)
        except Exception as e:
            results.append(type(e))

    # 동시에 15명의 사용자가 요청을 보낸다고 가정
    threads = []
    for _ in range(15):
        t = threading.Thread(target=call_api)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # 모든 요청이 성공(200)했는지 확인
    # 만약 maxconnections=10이고 blocking=True라면, 순차적으로 모두 200
    print(f"성공한 요청 개수: {results.count(200)}")
    assert all(res == 200 for res in results)
```

<br>

### 3-3. 결과

```
test/db_connect/cursor/user_test.py::test_db_access_by_connection_pool 
---------------------------------------------------------------------------------------------------------------- live log call -----------------------------------------------------------------------------------------------------------------
18:11:02 [INFO] [cursor] get_db_connection
18:11:02 [INFO] [cursor] get_db_connection
18:11:02 [INFO] [cursor] get_db_connection
18:11:02 [INFO] [After Get Connection] Waiting Time: 0.00s, Pool Stats: active=1, idle=4, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c216010>
18:11:02 [INFO] [cursor] get_db_connection
18:11:02 [INFO] [cursor] get_db_connection
18:11:02 [INFO] [cursor] get_db_connection
18:11:02 [INFO] [After Get Connection] Waiting Time: 0.00s, Pool Stats: active=2, idle=3, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c27b110>
18:11:02 [INFO] [After Get Connection] Waiting Time: 0.00s, Pool Stats: active=3, idle=2, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c299190>
18:11:02 [INFO] [cursor] get_db_connection
18:11:02 [INFO] [cursor] get_db_connection
18:11:02 [INFO] [cursor] get_db_connection
18:11:02 [INFO] [After Get Connection] Waiting Time: 0.00s, Pool Stats: active=4, idle=1, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c29b290>
18:11:02 [INFO] [cursor] get_db_connection
18:11:02 [INFO] [cursor] get_db_connection
18:11:02 [INFO] [cursor] get_db_connection
18:11:02 [INFO] [After Get Connection] Waiting Time: 0.00s, Pool Stats: active=5, idle=0, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c2ad210>
18:11:02 [INFO] [cursor] get_db_connection
18:11:02 [INFO] [cursor] get_db_connection
18:11:02 [INFO] [cursor] get_db_connection
18:11:02 [INFO] [After Get Connection] Waiting Time: 0.00s, Pool Stats: active=6, idle=0, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c2794d0>
18:11:02 [INFO] [After Get Connection] Waiting Time: 0.00s, Pool Stats: active=7, idle=0, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c289bd0>
18:11:02 [INFO] [After Get Connection] Waiting Time: 0.00s, Pool Stats: active=8, idle=0, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c299f10>
18:11:02 [INFO] [After Get Connection] Waiting Time: 0.00s, Pool Stats: active=9, idle=0, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c299110>
18:11:02 [INFO] [After Get Connection] Waiting Time: 0.00s, Pool Stats: active=10, idle=0, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c29a010>
18:11:05 [INFO] [Before Close Connection] Pool Stats: active=10, idle=0, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c299110>
18:11:05 [INFO] [Before Close Connection] Pool Stats: active=10, idle=0, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c216010>
18:11:05 [INFO] [cursor] db_connection_close ( pool return )
18:11:05 [INFO] [cursor] db_connection_close ( pool return )
18:11:05 [INFO] [Before Close Connection] Pool Stats: active=10, idle=0, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c27b110>
18:11:05 [INFO] [Before Close Connection] Pool Stats: active=10, idle=0, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c29b290>
18:11:05 [INFO] [After Close Connection] Pool Stats: active=9, idle=1
18:11:05 [INFO] [Before Close Connection] Pool Stats: active=9, idle=1, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c289bd0>
18:11:05 [INFO] [Before Close Connection] Pool Stats: active=9, idle=1, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c2794d0>
18:11:05 [INFO] [Before Close Connection] Pool Stats: active=9, idle=1, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c2ad210>
18:11:05 [INFO] [cursor] db_connection_close ( pool return )
18:11:05 [INFO] [Before Close Connection] Pool Stats: active=9, idle=1, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c299190>
18:11:05 [INFO] [After Close Connection] Pool Stats: active=8, idle=2
18:11:05 [INFO] [cursor] db_connection_close ( pool return )
18:11:05 [INFO] [cursor] db_connection_close ( pool return )
18:11:05 [INFO] [cursor] db_connection_close ( pool return )
18:11:05 [INFO] [After Get Connection] Waiting Time: 3.01s, Pool Stats: active=9, idle=1, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c29b550>
18:11:05 [INFO] [Before Close Connection] Pool Stats: active=9, idle=1, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c29a010>
18:11:05 [INFO] [cursor] db_connection_close ( pool return )
18:11:05 [INFO] [cursor] db_connection_close ( pool return )
18:11:05 [INFO] [After Get Connection] Waiting Time: 3.01s, Pool Stats: active=10, idle=0, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c28a850>
18:11:05 [INFO] [Before Close Connection] Pool Stats: active=10, idle=0, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c299f10>
18:11:05 [INFO] [After Close Connection] Pool Stats: active=9, idle=1
18:11:05 [INFO] [cursor] db_connection_close ( pool return )
18:11:05 [INFO] [After Close Connection] Pool Stats: active=8, idle=2
18:11:05 [INFO] [cursor] db_connection_close ( pool return )
18:11:05 [INFO] [After Close Connection] Pool Stats: active=7, idle=3
18:11:05 [INFO] [After Close Connection] Pool Stats: active=6, idle=4
18:11:05 [INFO] HTTP Request: GET http://testserver/cursor/users/ "HTTP/1.1 200 OK"
18:11:05 [INFO] HTTP Request: GET http://testserver/cursor/users/ "HTTP/1.1 200 OK"
18:11:05 [INFO] [After Get Connection] Waiting Time: 3.02s, Pool Stats: active=7, idle=3, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c1fa150>
18:11:05 [INFO] [After Close Connection] Pool Stats: active=6, idle=4
18:11:05 [INFO] [After Get Connection] Waiting Time: 3.02s, Pool Stats: active=7, idle=3, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c195a50>
18:11:05 [INFO] HTTP Request: GET http://testserver/cursor/users/ "HTTP/1.1 200 OK"
18:11:05 [INFO] HTTP Request: GET http://testserver/cursor/users/ "HTTP/1.1 200 OK"
18:11:05 [INFO] [After Close Connection] Pool Stats: active=6, idle=4
18:11:05 [INFO] HTTP Request: GET http://testserver/cursor/users/ "HTTP/1.1 200 OK"
18:11:05 [INFO] [After Get Connection] Waiting Time: 3.02s, Pool Stats: active=7, idle=3, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c242fd0>
18:11:05 [INFO] HTTP Request: GET http://testserver/cursor/users/ "HTTP/1.1 200 OK"
18:11:05 [INFO] [After Close Connection] Pool Stats: active=6, idle=4
18:11:05 [INFO] [After Close Connection] Pool Stats: active=5, idle=5
18:11:05 [INFO] HTTP Request: GET http://testserver/cursor/users/ "HTTP/1.1 200 OK"
18:11:05 [INFO] HTTP Request: GET http://testserver/cursor/users/ "HTTP/1.1 200 OK"
18:11:05 [INFO] HTTP Request: GET http://testserver/cursor/users/ "HTTP/1.1 200 OK"
18:11:05 [INFO] HTTP Request: GET http://testserver/cursor/users/ "HTTP/1.1 200 OK"
18:11:08 [INFO] [Before Close Connection] Pool Stats: active=5, idle=5, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c29b550>
18:11:08 [INFO] [Before Close Connection] Pool Stats: active=5, idle=5, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c28a850>
18:11:08 [INFO] [cursor] db_connection_close ( pool return )
18:11:08 [INFO] [cursor] db_connection_close ( pool return )
18:11:08 [INFO] [After Close Connection] Pool Stats: active=4, idle=6
18:11:08 [INFO] [After Close Connection] Pool Stats: active=3, idle=7
18:11:08 [INFO] [Before Close Connection] Pool Stats: active=3, idle=7, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c1fa150>
18:11:08 [INFO] [cursor] db_connection_close ( pool return )
18:11:08 [INFO] [Before Close Connection] Pool Stats: active=3, idle=7, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c195a50>
18:11:08 [INFO] [After Close Connection] Pool Stats: active=2, idle=8
18:11:08 [INFO] [cursor] db_connection_close ( pool return )
18:11:08 [INFO] HTTP Request: GET http://testserver/cursor/users/ "HTTP/1.1 200 OK"
18:11:08 [INFO] [After Close Connection] Pool Stats: active=1, idle=9
18:11:08 [INFO] HTTP Request: GET http://testserver/cursor/users/ "HTTP/1.1 200 OK"
18:11:08 [INFO] HTTP Request: GET http://testserver/cursor/users/ "HTTP/1.1 200 OK"
18:11:08 [INFO] HTTP Request: GET http://testserver/cursor/users/ "HTTP/1.1 200 OK"
18:11:08 [INFO] [Before Close Connection] Pool Stats: active=1, idle=9, connection=<dbutils.pooled_db.PooledDedicatedDBConnection object at 0x10c242fd0>
18:11:08 [INFO] [cursor] db_connection_close ( pool return )
18:11:08 [INFO] [After Close Connection] Pool Stats: active=0, idle=10
18:11:08 [INFO] HTTP Request: GET http://testserver/cursor/users/ "HTTP/1.1 200 OK"
성공한 요청 개수: 15
PASSED
```

처음 시작 시, mincached 에 의해 active 와 idle 의 합계가 5인 것을 확인할 수 있습니다.

maxconnections 을 10으로 설정하여 connection 이 계속 증가하다가 10에서 멈추는 것을 확인할 수 있습니다.

blocking=True 로 설정하여 커넥션을 갖지 못한 5개의 요청은 대기 후 connection 을 획득하는 것을 확인할 수 있습니다.

maxcached 를 10으로 설정하여, 테스트 종료 후 계속해서 커넥션 풀에 10개의 커넥션이 유지되는 것을 확인할 수 있습니다.

<br><br>

## Q. 왜 Router 에서 DB 연결을 주입받는지?

### 1. 트랜잭션의 범위(Transaction Boundary) 설정

- 상황: 하나의 Router에서 User 서비스와 Log 서비스 두 개를 호출한다고 가정해 봅시다.

- 이유: 만약 두 서비스가 각각 별도의 DB 세션을 생성해서 쓰면, 유저 저장은 성공했는데 로그 저장이 실패했을 때 전체 롤백(Rollback)이 불가능해집니다.

- 해결: Router에서 하나의 db 세션을 생성해 두 서비스에 **이 세션 하나로 다 처리해**라고 넘겨주면, 마지막에 Router가 끝날 때 한 번에 커밋하거나 롤백할 수 있습니다.

<br>

### 2. 세션 생명주기(Lifecycle) 관리

FastAPI의 Depends(get_db)는 HTTP 요청이 들어올 때 세션을 열고, 응답이 나갈 때 세션을 닫아주는(close) 역할을 합니다.

Router에서 받는 이유: 요청의 시작과 끝을 관리하는 곳이 Router이기 때문입니다.

만약 Service 내부에서 DB를 직접 열고 닫으면, 코드가 중복되고 실수로 세션을 안 닫아서 DB 연결이 꽉 차버리는(Connection Leak) 사고가 나기 쉽습니다.

<br>

### 3. 서비스의 "순수성"과 테스트 용이성

서비스 계층은 "DB가 어떻게 연결되는지" 몰라도 되게끔 설계하는 것이 좋습니다.

- Decoupling: 서비스는 그저 "나한테 DB 세션만 주면 로직을 실행할게"라는 상태가 됩니다.

- Testability: 유닛 테스트를 할 때, 진짜 DB가 아니라 가짜(Mock) DB 세션을 서비스에 슥 넣어주기만 하면 됩니다. Router가 주입(Injection)을 담당해주기 때문에 가능한 구조입니다.