from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from modora.api.auth import require_current_user
from modora.api.v1.models import (
    ConversationCreateRequest,
    ConversationItem,
    ConversationListResponse,
    ConversationMessageItem,
    ConversationUpdateRequest,
    DocumentItem,
)
from modora.core.auth.service import AuthUser
from modora.core.persistence.conversations import (
    create_conversation,
    delete_conversation,
    list_conversations_for_user,
    update_conversation,
)
from modora.core.settings import Settings

router = APIRouter(tags=["conversations"])


def _serialize_conversation(payload: dict) -> ConversationItem:
    return ConversationItem(
        id=payload["id"],
        title=payload["title"],
        created_at=payload["created_at"],
        documents=[
            DocumentItem(
                id=doc["id"],
                original_name=doc["original_name"],
                storage_key=doc.get("storage_key"),
                status=doc["status"],
                created_at=doc["created_at"],
            )
            for doc in payload.get("documents", [])
        ],
        messages=[
            ConversationMessageItem(
                role=message["role"],
                content=message["content"],
                citations=message.get("citations", []),
                isTyping=False,
            )
            for message in payload.get("messages", [])
        ],
    )


@router.get("/conversations", response_model=ConversationListResponse)
def list_conversations(user: AuthUser = Depends(require_current_user)):
    settings = Settings.load()
    conversations = list_conversations_for_user(settings, user_id=user.id)
    return ConversationListResponse(
        conversations=[_serialize_conversation(item) for item in conversations]
    )


@router.post("/conversations", response_model=ConversationItem, status_code=201)
def create_conversation_endpoint(
    request: ConversationCreateRequest,
    user: AuthUser = Depends(require_current_user),
):
    settings = Settings.load()
    conversation = create_conversation(settings, user_id=user.id, title=request.title)
    payload = {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at,
        "documents": [],
        "messages": [],
    }
    return _serialize_conversation(payload)


@router.put("/conversations/{conversation_id}", response_model=ConversationItem)
def update_conversation_endpoint(
    conversation_id: str,
    request: ConversationUpdateRequest,
    user: AuthUser = Depends(require_current_user),
):
    settings = Settings.load()
    try:
        update_conversation(
            settings,
            user_id=user.id,
            conversation_id=conversation_id,
            title=request.title,
            document_ids=request.document_ids,
            messages=[message.model_dump() for message in request.messages],
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    conversations = list_conversations_for_user(settings, user_id=user.id)
    for conversation in conversations:
        if conversation["id"] == conversation_id:
            return _serialize_conversation(conversation)
    raise HTTPException(status_code=404, detail="conversation not found")


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation_endpoint(
    conversation_id: str,
    user: AuthUser = Depends(require_current_user),
):
    settings = Settings.load()
    delete_conversation(settings, user_id=user.id, conversation_id=conversation_id)
    return None
