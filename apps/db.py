"""
db.py — PostgreSQL connection management with connection pooling (Supabase).
"""
import os
from urllib.parse import urlparse, unquote
import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")

_pool: ThreadedConnectionPool | None = None


def _build_pool() -> ThreadedConnectionPool:
    url = urlparse(DATABASE_URL)
    return ThreadedConnectionPool(
        minconn=1,
        maxconn=10,
        host=unquote(url.hostname or ""),
        port=url.port or 5432,
        dbname=url.path.lstrip("/"),
        user=unquote(url.username or ""),
        password=unquote(url.password or ""),
        sslmode="require",
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def _get_pool() -> ThreadedConnectionPool:
    global _pool
    if _pool is None or _pool.closed:
        _pool = _build_pool()
    return _pool


def get_conn():
    return _get_pool().getconn()


def put_conn(conn):
    _get_pool().putconn(conn)


def _adapt(sql: str) -> str:
    """Translate SQLite ? placeholders to PostgreSQL %s."""
    return sql.replace("?", "%s")


def query(sql, params=None):
    pool = _get_pool()
    conn = pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute(_adapt(sql), params or ())
        return [dict(r) for r in cur.fetchall()]
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def query_one(sql, params=None):
    pool = _get_pool()
    conn = pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute(_adapt(sql), params or ())
        row = cur.fetchone()
        return dict(row) if row else None
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def execute(sql, params=None):
    pool = _get_pool()
    conn = pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute(_adapt(sql), params or ())
        conn.commit()
        return cur.rowcount
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def execute_returning(sql, params=None):
    """Execute a query with a RETURNING clause and return the first row."""
    pool = _get_pool()
    conn = pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute(_adapt(sql), params or ())
        conn.commit()
        row = cur.fetchone()
        return dict(row) if row else None
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def migrate():
    """No-op — schema is managed by migrate_to_pg.py."""
    pass
