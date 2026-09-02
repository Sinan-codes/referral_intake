from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import get_connection, init_db, list_referrals, upsert_referrals
from app.duplicates.matcher import apply_duplicate_groups
from app.normalization.seed import normalize_seed_file


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = get_connection()
    init_db(conn)
    # Seed once: an empty table means this is a fresh db.sqlite3, not that
    # the seed file produced zero referrals (it doesn't).
    if not list_referrals(conn):
        referrals, _errors = normalize_seed_file()
        upsert_referrals(conn, apply_duplicate_groups(referrals))
    app.state.db = conn
    yield
    conn.close()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Hello World!"}