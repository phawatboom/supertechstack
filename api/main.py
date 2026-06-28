from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes.answers import router as answers_router
from app.routes.news import router as news_router
from app.routes.posts import router as posts_router
from app.routes.search import router as search_router
from app.routes.sources import router as sources_router
from app.routes.uploads import router as uploads_router
from app.routes.workspaces import router as workspaces_router

settings = get_settings()

app = FastAPI(title="SuperTechStack")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workspaces_router)
app.include_router(news_router)
app.include_router(sources_router)
app.include_router(posts_router)
app.include_router(search_router)
app.include_router(answers_router)
app.include_router(uploads_router)


@app.get("/")
def read_root():
    return {
        "message": "SuperTechStack is running",
        "status": "ok"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }
