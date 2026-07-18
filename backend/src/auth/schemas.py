"""Pydantic schemas for auth and API payloads."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from src.auth.personas import ALLOWED_ROLES, DEFAULT_ROLE, is_valid_role, normalize_role


UserRole = Literal[
    "individual",
    "lawyer",
    "chartered_accountant",
    "business_owner",
    "hr_professional",
    "student",
]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)
    role: UserRole = Field(
        ...,
        description=(
            "Product persona: individual | lawyer | chartered_accountant | "
            "business_owner | hr_professional | student"
        ),
    )
    accept_disclaimer: bool = Field(
        ...,
        description="Must be true — user must accept legal disclaimer",
    )

    @field_validator("role", mode="before")
    @classmethod
    def validate_role(cls, value: object) -> str:
        if value is None or str(value).strip() == "":
            raise ValueError(
                "role is required. Choose one of: "
                + ", ".join(sorted(ALLOWED_ROLES))
            )
        if not is_valid_role(str(value)):
            raise ValueError(
                "Invalid role. Allowed: " + ", ".join(sorted(ALLOWED_ROLES))
            )
        return normalize_role(str(value))


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email_verified: bool = False


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str | None
    role: str = DEFAULT_ROLE
    role_label: str = "Individual"
    welcome_message: str = ""
    created_at: datetime
    accepted_disclaimer_at: datetime | None
    email_verified: bool = False
    terms_version: str | None = None
    privacy_version: str | None = None
    plan: str = "free"
    org_id: str | None = None
    org_role: str | None = None
    document_count: int = 0

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    num_chunks: int
    file_size_bytes: int
    status: str
    processing_error: str | None = None
    page_count: int = 0
    has_tables: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class QuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    document_id: str


class CompareRequest(BaseModel):
    document_id_a: str
    document_id_b: str
    question: str = Field(
        default="Compare the key terms, obligations, payment, and termination clauses.",
        min_length=3,
        max_length=1000,
    )


class QuestionResponse(BaseModel):
    question: str
    answer: str
    question_type: str
    sources: list[dict]
    processing_time: float
    document_id: str
    message_id: str | None = None
    confidence_score: float | None = None
    confidence_level: Literal["High", "Medium", "Low"] | None = None
    recommendation: str | None = None
    confidence_factors: dict[str, float] | None = None


class ExplainSectionCitation(BaseModel):
    index: int
    page: int | str | None = None
    filename: str | None = None
    snippet: str | None = None
    document_id: str | None = None


class ExplainSection(BaseModel):
    id: str
    title: str
    content: str
    evidence_found: bool
    citations: list[ExplainSectionCitation] = Field(default_factory=list)


class ExplainRequest(BaseModel):
    document_id: str


class ExplainResponse(BaseModel):
    document_id: str
    filename: str
    sections: list[ExplainSection]
    sources: list[dict]
    processing_time: float
    message_id: str | None = None
    disclaimer: str
    confidence_score: float | None = None
    confidence_level: Literal["High", "Medium", "Low"] | None = None
    recommendation: str | None = None
    confidence_factors: dict[str, float] | None = None


class RiskCitation(BaseModel):
    index: int
    page: int | str | None = None
    filename: str | None = None
    snippet: str | None = None
    document_id: str | None = None


class RiskItem(BaseModel):
    id: str
    title: str
    explanation: str
    severity: Literal["Low", "Medium", "High"] | None = None
    evidence_found: bool
    citations: list[RiskCitation] = Field(default_factory=list)


class RiskRequest(BaseModel):
    document_id: str


class RiskResponse(BaseModel):
    document_id: str
    filename: str
    risks: list[RiskItem]
    sources: list[dict]
    processing_time: float
    message_id: str | None = None
    disclaimer: str
    flagged_count: int = 0
    confidence_score: float | None = None
    confidence_level: Literal["High", "Medium", "Low"] | None = None
    recommendation: str | None = None
    confidence_factors: dict[str, float] | None = None


ExpertCategory = Literal[
    "Property Lawyer",
    "Family Lawyer",
    "Corporate Lawyer",
    "Criminal Lawyer",
    "Civil Lawyer",
    "Employment Lawyer",
    "Tax Lawyer",
    "Chartered Accountant",
]


class ExpertRecommendRequest(BaseModel):
    document_id: str


class ExpertBasedOn(BaseModel):
    document: bool = False
    questions: bool = False
    risks: bool = False


class ExpertRecommendResponse(BaseModel):
    document_id: str
    filename: str
    category: ExpertCategory
    reason: str
    based_on: ExpertBasedOn
    detected_risks: list[str] = Field(default_factory=list)
    questions_considered: list[str] = Field(default_factory=list)
    sources: list[dict] = Field(default_factory=list)
    processing_time: float
    message_id: str | None = None
    disclaimer: str
    category_scores: dict[str, int] | None = None


class ConsultationSectionCitation(BaseModel):
    index: int
    page: int | str | None = None
    filename: str | None = None
    snippet: str | None = None
    document_id: str | None = None


class ConsultationSection(BaseModel):
    id: str
    title: str
    content: str
    items: list[str] = Field(default_factory=list)
    evidence_found: bool
    citations: list[ConsultationSectionCitation] = Field(default_factory=list)


class ConsultationRequest(BaseModel):
    document_id: str


class ConsultationResponse(BaseModel):
    document_id: str
    filename: str
    sections: list[ConsultationSection]
    sources: list[dict]
    processing_time: float
    message_id: str | None = None
    disclaimer: str
    export_filename: str


class ProfessionalCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    specialization: str = Field(
        min_length=1,
        max_length=100,
        description="Prefer expert categories, e.g. Property Lawyer",
    )
    city: str = Field(min_length=1, max_length=120)
    state: str = Field(default="", max_length=120)
    country: str = Field(default="", max_length=120)
    phone: str | None = Field(default=None, max_length=64)
    email: EmailStr | None = None
    website: str | None = Field(default=None, max_length=512)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    verified: bool = False


class ProfessionalUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    specialization: str | None = Field(default=None, min_length=1, max_length=100)
    city: str | None = Field(default=None, min_length=1, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=64)
    email: EmailStr | None = None
    website: str | None = Field(default=None, max_length=512)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    verified: bool | None = None


class ProfessionalResponse(BaseModel):
    id: str
    name: str
    specialization: str
    city: str
    state: str = ""
    country: str = ""
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    verified: bool = False
    source: str = "manual"
    external_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ProfessionalRecommendResponse(ProfessionalResponse):
    """Directory match enriched for recommendation UI."""

    practice_area: str = ""
    distance_km: float | None = None
    specialization_match: float = 0.0
    city_match: bool = False


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    question_type: str | None = None
    processing_time: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    message: str
    document: DocumentResponse


class UsageResponse(BaseModel):
    questions_last_hour: int
    uploads_last_hour: int
    questions_limit: int
    uploads_limit: int
    documents_owned: int
    documents_limit: int


class OrgCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)


class OrgInviteRequest(BaseModel):
    email: EmailStr
    role: str = Field(default="member", pattern="^(admin|member)$")


class GoogleAuthRequest(BaseModel):
    id_token: str
    accept_disclaimer: bool = False


class CheckoutRequest(BaseModel):
    success_url: str | None = None
    cancel_url: str | None = None
