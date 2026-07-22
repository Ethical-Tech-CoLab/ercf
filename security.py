"""
Abuse protection for the public ERCF API.

Protects the endpoints that spend money or third-party quota on behalf of
anonymous callers (Anthropic, EIA, FRED, GeoNames, ACAPS, UCDP) with:

  * per-IP sliding-window rate limits (always on, no configuration required)
  * a per-IP hourly budget plus a global daily cap on paid-LLM calls; once
    either is exhausted the endpoint degrades to the free static analysis
    instead of failing, so the UI keeps working
  * optional hard authentication, enabled only when API_KEY is set
  * a CORS allowlist instead of wide-open cross-origin access

Everything is stdlib + Starlette; no new dependencies. All limits are
env-tunable, and every default is chosen so an unconfigured deployment keeps
working exactly as before for normal human traffic.

Environment variables
---------------------
API_KEY                     If set, PROTECTED_PREFIXES require a matching
                            X-API-Key header (or ?api_key=). Unset = open.
ALLOWED_ORIGINS             Comma-separated CORS allowlist ("*" to disable
                            the restriction).
RATE_LIMIT_PER_MIN          Per-IP requests/min against /api/* (default 120).
EXTERNAL_RATE_LIMIT_PER_HOUR Per-IP requests/hour against third-party-backed
                            endpoints (default 120).
LLM_RATE_LIMIT_PER_HOUR     Per-IP paid-LLM calls/hour (default 10).
LLM_DAILY_CAP               Global paid-LLM calls/day across all callers
                            (default 500). 0 = never call the paid API.
"""

import hmac
import os
import threading
import time
from collections import deque

from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware


# ─── Config ──────────────────────────────────────────────────────────────────

def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default


API_KEY = os.environ.get("API_KEY", "").strip()

DEFAULT_ORIGINS = (
    "https://ercf-production.up.railway.app,"
    "http://localhost:8000,http://127.0.0.1:8000"
)
ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get("ALLOWED_ORIGINS", DEFAULT_ORIGINS).split(",")
    if o.strip()
]

RATE_LIMIT_PER_MIN           = _int_env("RATE_LIMIT_PER_MIN", 120)
EXTERNAL_RATE_LIMIT_PER_HOUR = _int_env("EXTERNAL_RATE_LIMIT_PER_HOUR", 120)
LLM_RATE_LIMIT_PER_HOUR      = _int_env("LLM_RATE_LIMIT_PER_HOUR", 10)
LLM_DAILY_CAP                = _int_env("LLM_DAILY_CAP", 500)

# Paid Anthropic call — one request costs the owner real money.
LLM_PREFIXES = ("/api/country-context",)

# Third-party quota (EIA / FRED / GeoNames / ACAPS / UCDP / Open-Meteo).
EXTERNAL_PREFIXES = (
    "/api/country-context-acaps",
    "/api/acaps",
    "/api/commodity-prices",
    "/api/city-population",
    "/api/ucdp",
    "/api/climate",
)

# Endpoints gated by API_KEY when (and only when) one is configured.
PROTECTED_PREFIXES = LLM_PREFIXES + EXTERNAL_PREFIXES


def _matches(path: str, prefixes) -> bool:
    return any(path == p or path.startswith(p + "/") for p in prefixes)


# ─── Sliding-window counters ─────────────────────────────────────────────────

class SlidingWindowLimiter:
    """In-memory per-key sliding window. Process-local by design: the app runs
    as a single uvicorn worker, and an approximate limit beats none."""

    def __init__(self, limit: int, window_s: int, max_keys: int = 10_000):
        self.limit = limit
        self.window_s = window_s
        self.max_keys = max_keys
        self._hits: dict[str, deque] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> tuple[bool, int]:
        """Record a hit. Returns (allowed, retry_after_seconds)."""
        now = time.monotonic()
        cutoff = now - self.window_s
        with self._lock:
            if len(self._hits) > self.max_keys:
                self._prune(cutoff)
            q = self._hits.setdefault(key, deque())
            while q and q[0] <= cutoff:
                q.popleft()
            if len(q) >= self.limit:
                return False, max(1, int(q[0] + self.window_s - now) + 1)
            q.append(now)
            return True, 0

    def _prune(self, cutoff: float) -> None:
        for k in [k for k, q in self._hits.items() if not q or q[-1] <= cutoff]:
            self._hits.pop(k, None)


class DailyCap:
    """Global (not per-IP) counter that resets every 24h. Backstop against
    IP rotation / X-Forwarded-For spoofing on the paid endpoint."""

    def __init__(self, limit: int):
        self.limit = limit
        self._count = 0
        self._reset_at = time.monotonic() + 86_400
        self._lock = threading.Lock()

    def check(self) -> bool:
        with self._lock:
            now = time.monotonic()
            if now >= self._reset_at:
                self._count = 0
                self._reset_at = now + 86_400
            if self._count >= self.limit:
                return False
            self._count += 1
            return True

    @property
    def used(self) -> int:
        return self._count


_general_limiter  = SlidingWindowLimiter(RATE_LIMIT_PER_MIN, 60)
_external_limiter = SlidingWindowLimiter(EXTERNAL_RATE_LIMIT_PER_HOUR, 3_600)
_llm_limiter      = SlidingWindowLimiter(LLM_RATE_LIMIT_PER_HOUR, 3_600)
_llm_daily_cap    = DailyCap(LLM_DAILY_CAP)


# ─── Client identification ───────────────────────────────────────────────────

def client_ip(request) -> str:
    """Best-effort client IP.

    Behind a single reverse proxy (Railway) the rightmost X-Forwarded-For entry
    is the one the proxy itself appended, so client-supplied values prepended by
    an attacker cannot be used to mint fresh rate-limit buckets.
    """
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            return parts[-1]
    return getattr(request.client, "host", None) or "unknown"


def llm_budget_ok(request) -> bool:
    """Consume one unit of paid-LLM budget for this caller.

    Returns False when the caller's hourly allowance or the deployment's daily
    allowance is exhausted; callers must then serve the free static analysis
    rather than billing the owner's Anthropic account.
    """
    allowed, _ = _llm_limiter.check(client_ip(request))
    if not allowed:
        return False
    return _llm_daily_cap.check()


def _too_many(detail: str, retry_after: int) -> JSONResponse:
    return JSONResponse(
        {"detail": detail},
        status_code=429,
        headers={"Retry-After": str(retry_after)},
    )


# ─── Installation ────────────────────────────────────────────────────────────

def install(app) -> None:
    """Attach the CORS allowlist and the throttling/auth middleware."""

    @app.middleware("http")
    async def _throttle(request, call_next):
        path = request.url.path
        if request.method == "OPTIONS" or not path.startswith("/api/"):
            return await call_next(request)

        ip = client_ip(request)

        ok, retry = _general_limiter.check(ip)
        if not ok:
            return _too_many("Rate limit exceeded. Slow down.", retry)

        if _matches(path, PROTECTED_PREFIXES) and API_KEY:
            supplied = (
                request.headers.get("x-api-key")
                or request.query_params.get("api_key")
                or ""
            )
            # Constant-time comparison; length leak is not meaningful here.
            if not hmac.compare_digest(supplied, API_KEY):
                return JSONResponse({"detail": "Invalid or missing API key."},
                                    status_code=401)

        if _matches(path, EXTERNAL_PREFIXES):
            ok, retry = _external_limiter.check(ip)
            if not ok:
                return _too_many(
                    "Hourly limit for live-data endpoints exceeded.", retry)

        # The paid-LLM budget is enforced inside the endpoint itself
        # (see llm_budget_ok) so exhaustion degrades to static analysis
        # instead of erroring out the UI.

        return await call_next(request)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Key"],
    )
