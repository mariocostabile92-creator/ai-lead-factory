from sqlalchemy.orm import Session
from datetime import datetime

from backend.models.conversation import Conversation, ConversationMessage
from backend.models.lead import Lead
from backend.schemas.common import AssistantRequest, AssistantResponse, BusinessContext
from backend.schemas.storage import ConversationHistory, ConversationMessageItem, LeadSummary


def save_lead(db: Session, payload: AssistantRequest, result: AssistantResponse) -> Lead:
    lead = Lead(
        business_name=payload.business.business_name,
        sector=payload.business.sector,
        location=payload.business.location,
        goal=payload.goal,
        details=payload.business.details,
        module=result.module,
        title=result.title,
        summary=result.summary,
        output=result.output,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def list_recent_leads(db: Session, limit: int = 6) -> list[LeadSummary]:
    items = db.query(Lead).order_by(Lead.created_at.desc()).limit(limit).all()
    return [
        LeadSummary(
            id=item.id,
            business_name=item.business_name,
            sector=item.sector,
            location=item.location,
            title=item.title,
            module=item.module,
            created_at=item.created_at,
        )
        for item in items
    ]


def get_or_create_conversation(db: Session, conversation_id: str | None, business: BusinessContext | None) -> Conversation:
    conversation = None
    if conversation_id:
        conversation = db.get(Conversation, conversation_id)

    if conversation is None:
        conversation = Conversation(
            business_name=(business.business_name if business else ""),
            sector=(business.sector if business else ""),
            location=(business.location if business else ""),
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    return conversation


def save_chat_turn(
    db: Session,
    conversation: Conversation,
    user_message: str,
    assistant_message: str,
    module: str,
) -> None:
    db.add(
        ConversationMessage(
            conversation_id=conversation.id,
            role="user",
            content=user_message,
            module=module,
        )
    )
    db.add(
        ConversationMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=assistant_message,
            module=module,
        )
    )
    conversation.updated_at = datetime.utcnow()
    db.commit()


def get_conversation_history(db: Session, conversation_id: str) -> ConversationHistory:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        return ConversationHistory(conversation_id=conversation_id, messages=[])

    messages = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.created_at.asc(), ConversationMessage.id.asc())
        .all()
    )
    return ConversationHistory(
        conversation_id=conversation.id,
        messages=[
            ConversationMessageItem(
                id=item.id,
                role=item.role,
                content=item.content,
                module=item.module,
                created_at=item.created_at,
            )
            for item in messages
        ],
    )
