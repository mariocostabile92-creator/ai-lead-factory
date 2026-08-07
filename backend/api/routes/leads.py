from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.db.session import get_db
from backend.schemas.storage import LeadSummary
from backend.services.store import list_recent_leads

router = APIRouter()


@router.get("/recent", response_model=list[LeadSummary])
def recent(limit: int = Query(default=6, ge=1, le=20), db: Session = Depends(get_db)) -> list[LeadSummary]:
    if not settings.enable_public_storage:
        return []
    return list_recent_leads(db, limit=limit)
