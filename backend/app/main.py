import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.scan import router as scan_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Bullish Breakout Scanner API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    # Include the IPv6 loopback: the dev server and the container both listen
    # on ::1, and an origin of http://[::1]:5174 must not be rejected.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|\[::1\]):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scan_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
