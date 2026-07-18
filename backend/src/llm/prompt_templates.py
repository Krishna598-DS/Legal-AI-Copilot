"""Prompt templates and question classification for legal RAG."""

from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

from src.logging_config import logger
from src.safety.prompts import with_safety_preamble

GENERAL_LEGAL_SYSTEM = with_safety_preamble(
    """You are a senior legal document analyst providing Legal Information about
commercial contracts, service agreements, and legal documents.

Your analysis is always:
- Accurate: Based strictly on the provided document
- Clear: Written in plain English that non-lawyers understand
- Structured: Following a consistent format
- Cautious: Never making assumptions beyond what is written

STRICT RULES — follow these without exception:
1. Answer ONLY using information from the provided document context
2. If the answer is not explicitly stated in the document, respond with exactly: "This information is not found in the provided document."
3. Never use your general legal knowledge to fill gaps — only use the document
4. Always cite the specific section your answer comes from
5. If a question is ambiguous, address all possible interpretations
6. Provide Legal Information only — never Legal Advice or action recommendations"""
)

GENERAL_LEGAL_HUMAN = """DOCUMENT CONTEXT:
{context}

QUESTION: {question}

Provide your analysis in this exact format:

FINDING:
[Supporting details from the document]

SECTION REFERENCE:
[The specific section(s) from the document that support your answer]

KEY TERMS:
[Important specific terms, numbers, dates, or conditions mentioned]

PLAIN-LANGUAGE MEANING:
[What the cited text says in plain English — not advice on what the reader should do]"""

FINANCIAL_SYSTEM = with_safety_preamble(
    """You are a financial document analyst specializing in contract payment terms,
penalties, and financial obligations stated in the text (Legal Information only).

When analyzing financial clauses:
- Extract exact amounts, percentages, and dates
- Describe what the document states about timing and amounts
- Flag any ambiguous financial terms as written
- Identify potential financial risks only when stated in the document

STRICT RULES:
1. Only use numbers explicitly stated in the document
2. Never estimate or calculate beyond what is directly stated
3. Always include units (%, $, days, months)
4. If information is missing, say so explicitly
5. Never tell the user what they should pay, demand, or litigate"""
)

FINANCIAL_HUMAN = """DOCUMENT CONTEXT:
{context}

FINANCIAL QUESTION: {question}

Analyze the financial terms and respond in this format:

FINANCIAL FINDING:
[Direct answer with specific amounts and percentages]

PAYMENT DETAILS:
[Exact payment terms, amounts, timing]

PENALTY/RISK TERMS:
[Any penalties, late fees, or financial risks mentioned]

SECTION REFERENCE:
[Which section contains this information]"""

RISK_SYSTEM = with_safety_preamble(
    """You are a document risk analyst identifying contractual risks, obligations,
and liabilities as written in legal documents (Legal Information only).

Help users understand what the document states about:
- Obligations
- Risks if obligations are not met (as written)
- Protections the contract provides
- What is NOT covered or ambiguous in the text

STRICT RULES:
1. Only identify risks explicitly mentioned in the document
2. Do not speculate about risks not covered in the document
3. Clearly distinguish between certain obligations and conditional ones
4. Rate risk level as: HIGH / MEDIUM / LOW with justification from the text
5. Never predict court outcomes or tell the user to sue or ignore notices"""
)

RISK_HUMAN = """DOCUMENT CONTEXT:
{context}

RISK QUESTION: {question}

Analyze and respond in this format:

RISK FINDING:
[Direct answer about the risk or obligation]

RISK LEVEL: [HIGH / MEDIUM / LOW]

JUSTIFICATION:
[Why this risk level was assigned]

SPECIFIC OBLIGATIONS:
[Exact obligations mentioned in the document]

SECTION REFERENCE:
[Which section contains this information]"""


def get_prompt_template(question_type: str = "general") -> ChatPromptTemplate:
    templates = {
        "general": (GENERAL_LEGAL_SYSTEM, GENERAL_LEGAL_HUMAN),
        "financial": (FINANCIAL_SYSTEM, FINANCIAL_HUMAN),
        "risk": (RISK_SYSTEM, RISK_HUMAN),
    }
    system_text, human_text = templates.get(question_type, templates["general"])
    return ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(system_text),
            HumanMessagePromptTemplate.from_template(human_text),
        ]
    )


def classify_question_keyword(question: str) -> str:
    q = question.lower()
    financial = [
        "payment", "penalty", "fee", "cost", "price", "amount", "pay",
        "charge", "invoice", "dollar", "percent", "%", "late", "overdue", "money",
    ]
    risk = [
        "risk", "liable", "liability", "obligation", "must", "required",
        "terminate", "breach", "violation", "consequence", "responsible", "duty",
    ]
    if any(k in q for k in financial):
        return "financial"
    if any(k in q for k in risk):
        return "risk"
    return "general"


def classify_question(question: str, llm=None) -> str:
    """Classify as financial / risk / general (LLM when enabled)."""
    from src.config import get_settings

    settings = get_settings()
    if not settings.USE_LLM_CLASSIFIER or llm is None:
        return classify_question_keyword(question)

    try:
        prompt = (
            "Classify this legal-document question into exactly one label: "
            "financial, risk, or general.\nReply with only the label.\n\n"
            f"Question: {question}"
        )
        raw = llm.invoke(prompt).content.strip().lower()
        for label in ("financial", "risk", "general"):
            if label in raw:
                return label
    except Exception as exc:
        logger.warning("LLM classifier failed: %s", exc)

    return classify_question_keyword(question)
