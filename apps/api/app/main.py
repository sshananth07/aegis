from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.logging import setup_logging
from app.core.config import settings
from app.api.routes import prompts, evaluations, benchmarks, reviews, metrics, exports

setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="Aegis API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
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

@app.get("/health")
def health():
    return {"status": "ok"}
