import threading

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

"""
# -s: 테스트 도중 출력되는 로그(Pool Stats 등)를 실시간으로 터미널에 표시
# -v: 테스트 케이스별 성공/실패 상세 결과 표시
pytest -s -v 경로/파일명.py
"""

# DB 커넥션 풀 테스트
# pytest -s -v test/db_connect/cursor/user_test.py
def test_db_access_by_connection_pool():
    results = []

    def call_api():
        try:
            # 숏커트: 실제 통신이 아닌 로직 테스트를 위해 client 사용
            response = client.get("/cursor/users/")
            results.append(response.status_code)
        except Exception as e:
            results.append(type(e))

    # 동시에 15명의 사용자가 요청을 보낸다고 가정 (풀 크기보다 크게 설정해 보세요)
    threads = []
    for _ in range(15):
        t = threading.Thread(target=call_api)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # 모든 요청이 성공(200)했는지 확인
    # 만약 maxconnections=10이고 blocking=True라면, 순차적으로 모두 200이 나옵니다.
    print(f"성공한 요청 개수: {results.count(200)}")
    assert all(res == 200 for res in results)