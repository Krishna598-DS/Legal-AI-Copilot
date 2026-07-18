"""Account, privacy, usage, billing stubs."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_usage_counts
from src.auth.schemas import CheckoutRequest, UsageResponse
from src.config import get_settings
from src.db.database import get_db
from src.db.models import User
from src.errors import ServiceUnavailableError, ValidationAppError
from src.services import document_service, rag_service
from src.services.document_service import list_documents

router = APIRouter(prefix="/account", tags=["account"])
settings = get_settings()

PRIVACY_TEXT = f"""
Privacy Policy — AI Legal Copilot (v{settings.PRIVACY_VERSION})

1. Data we store
   - Account email, name, and hashed password (or Google subject)
   - Uploaded documents and derived vector indexes
   - Chat questions and answers linked to your documents
   - Usage events for rate limiting
   - Terms/privacy version you accepted

2. How we use data
   - To answer questions about YOUR documents only
   - Documents and chats are isolated per account
   - We do not share your documents with other users

3. Third parties
   - Document text and questions are sent to OpenAI to generate
     embeddings and answers. Review OpenAI's data policies.
   - Optional: Stripe for billing, Google for SSO

4. Retention & deletion
   - You may delete individual documents at any time
   - You may delete your entire account; this removes your files,
     indexes, chat history, and account record

5. Not legal advice
   - This product helps you explore documents with AI.
   - It is not a substitute for a licensed attorney.
""".strip()


@router.get("/usage", response_model=UsageResponse)
def usage(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    counts = get_usage_counts(user.id, db)
    return UsageResponse(**counts)


@router.get("/privacy")
def privacy_policy():
    return {
        "title": "Privacy Policy",
        "version": settings.PRIVACY_VERSION,
        "content": PRIVACY_TEXT,
    }


@router.get("/disclaimer")
def disclaimer():
    return {
        "title": "Legal Disclaimer",
        "version": settings.TERMS_VERSION,
        "content": (
            "AI Legal Copilot helps you understand legal documents with AI. "
            "It does not provide legal advice, create an attorney-client "
            "relationship, or replace consultation with a qualified lawyer. "
            "Always verify important decisions with a licensed professional. "
            "Answers are generated from your uploaded document and may be incomplete."
        ),
    }


@router.delete("")
def delete_account(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    docs = list_documents(db, user)
    for doc in docs:
        rag_service.invalidate_rag(doc.id)
    document_service.delete_user_account(db, user)
    return {"message": "Account and all associated data deleted"}


@router.post("/billing/checkout")
def create_checkout(
    payload: CheckoutRequest,
    user: User = Depends(get_current_user),
):
    if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_PRICE_ID:
        raise ServiceUnavailableError(
            "Billing is not configured.",
            code="BILLING_UNAVAILABLE",
        )
    try:
        import stripe
    except ImportError as exc:
        raise ServiceUnavailableError(
            "Billing is not available on this server.",
            code="BILLING_UNAVAILABLE",
        ) from exc

    stripe.api_key = settings.STRIPE_SECRET_KEY
    success = payload.success_url or f"{settings.FRONTEND_URL}/?billing=success"
    cancel = payload.cancel_url or f"{settings.FRONTEND_URL}/?billing=cancel"
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": settings.STRIPE_PRICE_ID, "quantity": 1}],
        success_url=success,
        cancel_url=cancel,
        customer_email=user.email,
        client_reference_id=user.id,
        metadata={"user_id": user.id},
    )
    return {"checkout_url": session.url, "session_id": session.id}


@router.post("/billing/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_WEBHOOK_SECRET:
        raise ServiceUnavailableError(
            "Stripe webhook is not configured.",
            code="BILLING_UNAVAILABLE",
        )
    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig, settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception as exc:
        raise ValidationAppError(
            "Invalid webhook signature.",
            code="INVALID_WEBHOOK",
            details={"type": type(exc).__name__},
        ) from exc

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = (session.get("metadata") or {}).get("user_id") or session.get(
            "client_reference_id"
        )
        if user_id:
            user = db.get(User, user_id)
            if user:
                user.plan = "pro"
                user.stripe_customer_id = session.get("customer")
                db.commit()
    return {"received": True}
