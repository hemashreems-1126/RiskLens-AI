"""RiskLens AI — FastAPI entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database.db import init_db, SessionLocal
from app.api.routes import router
from app.config.settings import get_settings
from app.models import models
from app.services.data_generator import generate_dataset_for_db
from app.services import alert_service

settings = get_settings()

app = FastAPI(title="RiskLens AI", description="Autonomous Payment Risk Investigation & Decision System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def on_startup():
    init_db()
    # Auto-seed demo data on first boot so the dashboard is never empty.
    db: Session = SessionLocal()
    try:
        if db.query(models.Transaction).count() == 0:
            rows = generate_dataset_for_db()
            for row in rows:
                db.add(models.Transaction(**row))
            db.commit()
            alert_service.generate_alerts_for_all_transactions(db)
    finally:
        db.close()
