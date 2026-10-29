"""Create JewelryTryOn SQLite tables and print a quick status check."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.db import DATABASE_PATH, SessionLocal, init_db
from app.models import Generation, Upload


def main() -> None:
    init_db()
    with SessionLocal() as db:
        uploads = db.query(Upload).count()
        generations = db.query(Generation).count()
    print(f"Database ready: {DATABASE_PATH}")
    print(f"Tables: uploads, generations")
    print(f"Rows: uploads={uploads}, generations={generations}")


if __name__ == "__main__":
    main()
