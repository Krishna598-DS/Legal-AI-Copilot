"""Auth / API smoke checks (no OpenAI calls required for auth)."""

from fastapi.testclient import TestClient

from src.api.main import app
from src.db.database import SessionLocal, init_db
from src.db.models import User

init_db()
client = TestClient(app)

EMAIL = "smoke@example.com"
PASSWORD = "testpass123"


def main() -> None:
    db = SessionLocal()
    existing = db.query(User).filter(User.email == EMAIL).first()
    if existing:
        db.delete(existing)
        db.commit()
    db.close()

    r = client.post(
        "/auth/register",
        json={
            "email": EMAIL,
            "password": PASSWORD,
            "full_name": "Smoke",
            "role": "individual",
            "accept_disclaimer": True,
        },
    )
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]

    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    assert r.json()["email"] == EMAIL

    r = client.get("/documents", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json() == []

    r = client.get("/health")
    assert r.status_code == 200
    print("SMOKE OK", r.json())


if __name__ == "__main__":
    main()
