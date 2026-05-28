"""bcrypt 雜湊 + JWT encode/decode unit tests"""
from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_then_verify(self):
        h = hash_password("Tmca0001!")
        assert verify_password("Tmca0001!", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("Tmca0001!")
        assert verify_password("wrong", h) is False

    def test_hash_is_not_plaintext(self):
        h = hash_password("Tmca0001!")
        assert h != "Tmca0001!"
        assert h.startswith("$2")  # bcrypt prefix

    def test_hash_is_salted(self):
        # 每次 hash 同樣密碼應該不同（salt 隨機）
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2
        # 但都該 verify 通過
        assert verify_password("same", h1)
        assert verify_password("same", h2)


class TestJwt:
    def test_encode_decode_roundtrip(self):
        token = create_access_token({"user_id": 1, "role": "officer_a"})
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded["user_id"] == 1
        assert decoded["role"] == "officer_a"

    def test_exp_claim_is_set(self):
        token = create_access_token({"user_id": 1})
        decoded = decode_token(token)
        assert decoded is not None
        assert "exp" in decoded

    def test_expired_token_returns_none(self):
        # ttl_hours = -1 → 立刻過期
        token = create_access_token({"user_id": 1}, ttl_hours=-1)
        assert decode_token(token) is None

    def test_tampered_token_returns_none(self):
        token = create_access_token({"user_id": 1})
        assert decode_token(token + "tamper") is None

    def test_garbage_token_returns_none(self):
        assert decode_token("not.a.jwt") is None
        assert decode_token("") is None

    def test_payload_isolation(self):
        # 兩個不同 payload 不應互相污染
        t1 = create_access_token({"user_id": 1, "role": "officer_a"})
        t2 = create_access_token({"user_id": 2, "role": "accountant"})
        d1 = decode_token(t1)
        d2 = decode_token(t2)
        assert d1 is not None and d2 is not None
        assert d1["user_id"] == 1 and d1["role"] == "officer_a"
        assert d2["user_id"] == 2 and d2["role"] == "accountant"
