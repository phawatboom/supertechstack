from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import Base, engine
from app.models import workspace
from app.routes.workspaces import router as ws_router

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

app.include_router(ws_router)

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
