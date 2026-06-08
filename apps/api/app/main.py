from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.logging import setup_logging
from app.core.config import settings
from app.core.rate_limit import limiter
from app.api.routes import prompts, evaluations, benchmarks, reviews, metrics, exports, analytics, webhooks

setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate required environment variables at startup
    settings.validate_required()
    yield

app = FastAPI(title="Aegis API", lifespan=lifespan)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
origins = [o.strip() for o in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prompts.router)
app.include_router(evaluations.router)
app.include_router(benchmarks.router)
app.include_router(reviews.router)
app.include_router(metrics.router)
app.include_router(exports.router)
app.include_router(analytics.router)
app.include_router(webhooks.router)

@app.get("/health")
def health():
    return {"status": "ok"}
