import traceback

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from services.database import engine, get_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/db")
def db_health():
    """
    Readiness probe for the database. Runs a trivial round-trip so it's cheap
    enough for a load balancer to poll. Unauthenticated by design (probes have
    no token), so it never returns the raw exception — that could leak the
    server host/user from a driver error. The full error is logged instead.
    """
    try:
        with get_db() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected", "dialect": engine.dialect.name}
    except Exception as e:
        # Log the full detail server-side for deploy debugging; return only the
        # exception type to the caller (e.g. "OperationalError").
        print("\n" + "=" * 60)
        print("⚠️ DB HEALTH CHECK FAILED:")
        traceback.print_exc()
        print("=" * 60 + "\n")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "unreachable", "error": type(e).__name__},
        )
