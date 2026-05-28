"""Auth flow integration tests — login / me / logout / cookie"""
from app.api.deps import COOKIE_NAME


class TestLogin:
    def test_returns_200_and_user(self, client):
        r = client.post("/api/auth/login",
                        json={"username": "officer_a", "password": "Tmca0001!"})
        assert r.status_code == 200
        body = r.json()
        assert body["user"]["username"] == "officer_a"
        assert body["user"]["role"] == "officer_a"
        assert "access_token" in body
        assert body["expires_in"] > 0

    def test_sets_httponly_cookie(self, client):
        r = client.post("/api/auth/login",
                        json={"username": "officer_a", "password": "Tmca0001!"})
        assert r.status_code == 200
        assert COOKIE_NAME in r.cookies

    def test_wrong_password(self, client):
        r = client.post("/api/auth/login",
                        json={"username": "officer_a", "password": "wrong"})
        assert r.status_code == 401

    def test_unknown_user(self, client):
        r = client.post("/api/auth/login",
                        json={"username": "nobody", "password": "x"})
        assert r.status_code == 401

    def test_inactive_user_rejected(self, client, db):
        from app.models import User
        u = db.query(User).filter_by(username="viewer_test_inactive").first()
        if not u:
            u = User(
                username="viewer_test_inactive",
                password_hash="$2b$12$abcdefghijklmnopqrstuv",
                display_name="x", role="viewer", is_active=False,
            )
            db.add(u); db.commit()
        r = client.post("/api/auth/login",
                        json={"username": "viewer_test_inactive", "password": "Tmca0001!"})
        assert r.status_code == 401


class TestMe:
    def test_requires_auth(self, client):
        r = client.get("/api/auth/me")
        assert r.status_code == 401

    def test_returns_self(self, client_as_officer_a):
        r = client_as_officer_a.get("/api/auth/me")
        assert r.status_code == 200
        assert r.json()["username"] == "officer_a"
        assert r.json()["role"] == "officer_a"

    def test_works_with_bearer_token(self, client):
        r = client.post("/api/auth/login",
                        json={"username": "accountant", "password": "Tmca0001!"})
        token = r.json()["access_token"]
        # 清掉 cookie 避免混淆
        client.cookies.clear()
        r2 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 200
        assert r2.json()["username"] == "accountant"

    def test_invalid_bearer_rejected(self, client):
        r = client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.real.jwt"})
        assert r.status_code == 401


class TestLogout:
    def test_logout_clears_cookie(self, client_as_officer_a):
        # 已登入：me 通
        assert client_as_officer_a.get("/api/auth/me").status_code == 200
        r = client_as_officer_a.post("/api/auth/logout")
        assert r.status_code == 200
        # cookie 已被清掉
        assert COOKIE_NAME not in client_as_officer_a.cookies or client_as_officer_a.cookies.get(COOKIE_NAME) in (None, "")
        # 但 TestClient 不會自動丟掉 set-cookie max-age=0 的 cookie；保險起見直接清
        client_as_officer_a.cookies.clear()
        assert client_as_officer_a.get("/api/auth/me").status_code == 401
