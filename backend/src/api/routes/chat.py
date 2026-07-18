"""Chat / Q&A routes including streaming and compare."""

from fastapi import APIRouter, Depends
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from src.api.deps import enforce_question_rate_limit, get_current_user
from src.auth.schemas import (
    ChatMessageResponse,
    CompareRequest,
    ConsultationRequest,
    ConsultationResponse,
    ExpertRecommendRequest,
    ExpertRecommendResponse,
    ExplainRequest,
    ExplainResponse,
    QuestionRequest,
    QuestionResponse,
    RiskRequest,
    RiskResponse,
)
from src.db.database import get_db
from src.db.models import User
from src.services import (
    consultation_service,
    document_service,
    expert_service,
    explain_service,
    rag_service,
    risk_service,
)

router = APIRouter(tags=["chat"])


@router.post("/ask", response_model=QuestionResponse)
def ask_question(
    payload: QuestionRequest,
    user: User = Depends(enforce_question_rate_limit),
    db: Session = Depends(get_db),
):
    result = rag_service.ask_document(
        db, user, payload.document_id, payload.question
    )
    return QuestionResponse(**result)


@router.post("/explain", response_model=ExplainResponse)
def explain_document(
    payload: ExplainRequest,
    user: User = Depends(enforce_question_rate_limit),
    db: Session = Depends(get_db),
):
    """
    Automatically explain a document in plain language with citations.
    Grounded only in retrieved excerpts — missing evidence is stated explicitly.
    """
    result = explain_service.explain_document(db, user, payload.document_id)
    return ExplainResponse(**result)


@router.post(
    "/documents/{document_id}/explain",
    response_model=ExplainResponse,
)
def explain_document_by_id(
    document_id: str,
    user: User = Depends(enforce_question_rate_limit),
    db: Session = Depends(get_db),
):
    """Path-style alias for Explain My Document."""
    result = explain_service.explain_document(db, user, document_id)
    return ExplainResponse(**result)


@router.post("/risks", response_model=RiskResponse)
def highlight_risks(
    payload: RiskRequest,
    user: User = Depends(enforce_question_rate_limit),
    db: Session = Depends(get_db),
):
    """
    Highlight common legal risks with severity and citations.
    Unsupported checklist items return "No evidence found".
    """
    result = risk_service.analyze_document_risks(db, user, payload.document_id)
    return RiskResponse(**result)


@router.post(
    "/documents/{document_id}/risks",
    response_model=RiskResponse,
)
def highlight_risks_by_id(
    document_id: str,
    user: User = Depends(enforce_question_rate_limit),
    db: Session = Depends(get_db),
):
    """Path-style alias for legal risk highlighting."""
    result = risk_service.analyze_document_risks(db, user, document_id)
    return RiskResponse(**result)


@router.post("/prepare-consultation", response_model=ConsultationResponse)
def prepare_consultation(
    payload: ConsultationRequest,
    user: User = Depends(enforce_question_rate_limit),
    db: Session = Depends(get_db),
):
    """
    Prepare a grounded consultation briefing (summary, facts, timeline, risks,
    questions, documents to carry). Summarizes document contents only — not legal advice.
    """
    result = consultation_service.prepare_consultation(
        db, user, payload.document_id
    )
    return ConsultationResponse(**result)


@router.post(
    "/documents/{document_id}/prepare-consultation",
    response_model=ConsultationResponse,
)
def prepare_consultation_by_id(
    document_id: str,
    user: User = Depends(enforce_question_rate_limit),
    db: Session = Depends(get_db),
):
    """Path-style alias for Prepare for Consultation."""
    result = consultation_service.prepare_consultation(db, user, document_id)
    return ConsultationResponse(**result)


@router.post("/prepare-consultation/pdf")
def prepare_consultation_pdf(
    payload: ConsultationRequest,
    user: User = Depends(enforce_question_rate_limit),
    db: Session = Depends(get_db),
):
    """Generate the consultation briefing and return it as a downloadable PDF."""
    pdf_bytes, export_name, _prep = consultation_service.prepare_consultation_pdf(
        db, user, payload.document_id
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{export_name}"',
        },
    )


@router.post("/documents/{document_id}/prepare-consultation/pdf")
def prepare_consultation_pdf_by_id(
    document_id: str,
    user: User = Depends(enforce_question_rate_limit),
    db: Session = Depends(get_db),
):
    """Path-style PDF export for Prepare for Consultation."""
    pdf_bytes, export_name, _prep = consultation_service.prepare_consultation_pdf(
        db, user, document_id
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{export_name}"',
        },
    )


@router.post("/recommend-expert", response_model=ExpertRecommendResponse)
def recommend_expert(
    payload: ExpertRecommendRequest,
    user: User = Depends(enforce_question_rate_limit),
    db: Session = Depends(get_db),
):
    """
    Recommend a single expert category (never a specific professional)
    from the document, user questions, and detected risks.
    """
    result = expert_service.recommend_expert(db, user, payload.document_id)
    return ExpertRecommendResponse(**result)


@router.post(
    "/documents/{document_id}/recommend-expert",
    response_model=ExpertRecommendResponse,
)
def recommend_expert_by_id(
    document_id: str,
    user: User = Depends(enforce_question_rate_limit),
    db: Session = Depends(get_db),
):
    """Path-style alias for expert category recommendation."""
    result = expert_service.recommend_expert(db, user, document_id)
    return ExpertRecommendResponse(**result)


@router.post("/ask/stream")
def ask_question_stream(
    payload: QuestionRequest,
    user: User = Depends(enforce_question_rate_limit),
    db: Session = Depends(get_db),
):
    generator = rag_service.stream_ask_document(
        db, user, payload.document_id, payload.question
    )
    return StreamingResponse(generator, media_type="text/event-stream")


@router.post("/compare", response_model=QuestionResponse)
def compare_documents(
    payload: CompareRequest,
    user: User = Depends(enforce_question_rate_limit),
    db: Session = Depends(get_db),
):
    result = rag_service.compare_documents(
        db,
        user,
        payload.document_id_a,
        payload.document_id_b,
        payload.question,
    )
    return QuestionResponse(
        question=result["question"],
        answer=result["answer"],
        question_type=result["question_type"],
        sources=result["sources"],
        processing_time=result["processing_time"],
        document_id=result["document_id"],
        message_id=result.get("message_id"),
        confidence_score=result.get("confidence_score"),
        confidence_level=result.get("confidence_level"),
        recommendation=result.get("recommendation"),
        confidence_factors=result.get("confidence_factors"),
    )


@router.get(
    "/documents/{document_id}/messages",
    response_model=list[ChatMessageResponse],
)
def get_messages(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    messages = document_service.get_chat_history(db, user, document_id)
    return [ChatMessageResponse.model_validate(m) for m in messages]


@router.post("/documents/{document_id}/conversation/reset")
def reset_conversation(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rag_service.reset_conversation(db, user, document_id)
    return {"message": "Conversation history cleared"}


@router.get("/documents/{document_id}/export")
def export_conversation(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = document_service.get_user_document(db, user, document_id)
    messages = document_service.get_chat_history(db, user, document_id)

    lines = [
        "AI Legal Copilot — Conversation Export",
        f"Document: {doc.original_filename}",
        f"Exported for: {user.email}",
        "",
        "DISCLAIMER: This output is for informational purposes only "
        "and does not constitute legal advice.",
        "",
        "-" * 60,
        "",
    ]
    for msg in messages:
        role = "You" if msg.role == "user" else "Assistant"
        lines.append(f"{role}:")
        lines.append(msg.content)
        lines.append("")

    return {
        "filename": f"{doc.original_filename}_conversation.txt",
        "content": "\n".join(lines),
        "message_count": len(messages),
    }
