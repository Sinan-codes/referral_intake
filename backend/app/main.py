from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.db import get_connection, init_db, list_referrals, upsert_referrals
from app.duplicates.matcher import apply_duplicate_groups
from app.models.api import ErrorDetail, ErrorResponse
from app.normalization.seed import normalize_seed_file
from app.routers.referrals import router as referrals_router


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
app.include_router(referrals_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    # Routes raise HTTPException with an ErrorDetail-shaped dict as `detail`
    # so every error response matches the `ErrorResponse` envelope defined
    # in api.py, instead of FastAPI's default bare `{"detail": ...}`.
    detail = exc.detail
    error = (
        ErrorDetail(**detail)
        if isinstance(detail, dict) and "code" in detail
        else ErrorDetail(code="error", message=str(detail))
    )
    return JSONResponse(status_code=exc.status_code, content=ErrorResponse(error=error).model_dump())


@app.get("/")
async def root():
    return {"message": "Hello World!"}