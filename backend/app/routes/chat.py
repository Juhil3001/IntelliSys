from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import ChatMessage, Project
from app.modules.ai_engine import build_project_context

settings = get_settings()
router = APIRouter()


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=8000)


@router.post("/{project_id}/message")
def chat_message(
    project_id: int,
    body: ChatIn,
    db: Session = Depends(get_db),
) -> dict:
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    db.add(ChatMessage(project_id=project_id, role="user", content=body.message))
    db.commit()

    key = settings.openai_api_key_effective
    if not key:
        reply = "OpenAI is not configured. Set OPENAI_API_KEY in backend/.env or the process environment, then restart the API."
    else:
        from openai import OpenAI

        client = OpenAI(api_key=key)
        context = build_project_context(db, project_id)
        model = (settings.ai_issues_model or "gpt-4o-mini").strip() or "gpt-4o-mini"
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You answer questions about a monitored codebase and its APIs using the "
                        "provided context. If data is missing, say what is missing. Be concise."
                    ),
                },
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {body.message}"},
            ],
            max_tokens=1000,
        )
        reply = (resp.choices[0].message.content or "").strip()
    m = ChatMessage(project_id=project_id, role="assistant", content=reply)
    db.add(m)
    db.commit()
    return {"reply": reply}


@router.get("/{project_id}/history")
def history(
    project_id: int,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
) -> list[dict]:
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    q = (
        select(ChatMessage)
        .where(ChatMessage.project_id == project_id)
        .order_by(ChatMessage.id.desc())
        .limit(limit)
    )
    rows = list(db.execute(q).scalars().all())
    return [
        {
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in reversed(rows)
    ]
