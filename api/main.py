from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import Base, engine
from app.models import chunk, report, source, workspace
from app.routes.answers import router as answers_router
from app.routes.search import router as search_router
from app.routes.sources import router as sources_router
from app.routes.uploads import router as uploads_router
from app.routes.workspaces import router as workspaces_router


Base.metadata.create_all(bind=engine)

app = FastAPI(title="SuperTechStack")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workspaces_router)
app.include_router(sources_router)
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
