from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from models.document import Document
from models.user import User
from storage.database import get_db

router = APIRouter(tags=["Knowledge"])


@router.get("/knowledge")
def knowledge_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    docs = db.query(Document).filter(Document.tenant_id == current_user.tenant_id).all()
    return {
        "documents": [d.filename for d in docs],
        "document_count": len(docs),
        "companies": list(set(d.company for d in docs if d.company)),
    }


@router.get("/knowledge/statistics")
def knowledge_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    docs = db.query(Document).filter(Document.tenant_id == current_user.tenant_id).all()
    return {
        "documents": len(docs),
        "companies": len(set(d.company for d in docs if d.company)),
        "chunks": 0,
        "embeddings": 0,
    }