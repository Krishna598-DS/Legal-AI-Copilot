"""Quick route inventory smoke test."""

from src.api.main import app
from src.db.database import init_db

init_db()
paths = sorted(
    {getattr(r, "path", "") for r in app.routes if getattr(r, "path", None)}
)
print("OK routes:", len(paths))
for p in paths:
    print(p)
