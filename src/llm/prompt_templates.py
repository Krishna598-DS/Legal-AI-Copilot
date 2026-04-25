# prompt_templates.py
# PURPOSE: Production-grade prompt templates for legal document analysis
# Day 7: Prompt Engineering

from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate


# ============================================================
# TEMPLATE 1: GENERAL LEGAL ANALYSIS
# Used for: Most legal document questions
# Techniques: Role prompting, negative instructions,
#             format control, hallucination prevention
# ============================================================

GENERAL_LEGAL_SYSTEM = """You are a senior legal document analyst with 20 years of experience reviewing commercial contracts, service agreements, and legal documents.

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
6. Never provide legal advice — only document analysis"""

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

PRACTICAL IMPLICATION:
[What this means in plain English for someone reading this contract]"""


# ============================================================
# TEMPLATE 2: FINANCIAL TERMS ANALYSIS
# Used for: Questions about payments, penalties, costs
# Techniques: Few-shot example, chain of thought,
#             specific output format for numbers
# ============================================================

FINANCIAL_SYSTEM = """You are a financial and legal analyst specializing in contract payment terms, penalties, and financial obligations.

When analyzing financial clauses:
- Extract exact amounts, percentages, and dates
- Calculate practical implications where possible
- Flag any ambiguous financial terms
- Identify potential financial risks

STRICT RULES:
1. Only use numbers explicitly stated in the document
2. Never estimate or calculate beyond what is directly stated
3. Always include units (%, $, days, months)
4. If information is missing, say so explicitly"""

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


# ============================================================
# TEMPLATE 3: RISK ANALYSIS
# Used for: Questions about obligations, risks, liabilities
# Techniques: Role prompting with risk focus,
#             structured risk output
# ============================================================

RISK_SYSTEM = """You are a legal risk analyst who specializes in identifying contractual risks, obligations, and liabilities in legal documents.

Your job is to help clients understand:
- What they are obligated to do
- What risks they face if obligations are not met
- What protections the contract provides
- What is NOT covered or ambiguous

STRICT RULES:
1. Only identify risks explicitly mentioned in the document
2. Do not speculate about risks not covered in the document
3. Clearly distinguish between certain obligations and conditional ones
4. Rate risk level as: HIGH / MEDIUM / LOW with justification"""

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


# ============================================================
# TEMPLATE FACTORY
# Selects the right template based on question type
# ============================================================

def get_prompt_template(question_type: str = "general"):
    """
    Return the appropriate prompt template for the question type.

    Why a factory function?
    - Single place to manage all templates
    - Easy to add new templates as needed
    - Calling code doesn't need to know template details

    Args:
        question_type: "general", "financial", or "risk"

    Returns:
        ChatPromptTemplate ready for use with LangChain
    """

    templates = {
        "general": (GENERAL_LEGAL_SYSTEM, GENERAL_LEGAL_HUMAN),
        "financial": (FINANCIAL_SYSTEM, FINANCIAL_HUMAN),
        "risk": (RISK_SYSTEM, RISK_HUMAN)
    }

    # Default to general if unknown type provided
    system_text, human_text = templates.get(
        question_type,
        templates["general"]
    )

    # Build LangChain ChatPromptTemplate
    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system_text),
        HumanMessagePromptTemplate.from_template(human_text)
    ])

    return prompt


def classify_question(question: str) -> str:
    """
    Automatically detect what type of question is being asked.
    Routes to the most appropriate prompt template.

    This is a simple keyword-based classifier.
    In production you could use an LLM to classify more accurately.

    Args:
        question: User's question string

    Returns:
        Question type string: "financial", "risk", or "general"
    """
    question_lower = question.lower()

    # Financial keywords
    financial_keywords = [
        "payment", "penalty", "fee", "cost", "price",
        "amount", "pay", "charge", "invoice", "dollar",
        "percent", "%", "late", "overdue", "money"
    ]

    # Risk keywords
    risk_keywords = [
        "risk", "liable", "liability", "obligation", "must",
        "required", "terminate", "breach", "violation",
        "consequence", "responsible", "duty"
    ]

    if any(keyword in question_lower for keyword in financial_keywords):
        print("Question classified as: FINANCIAL")
        return "financial"

    if any(keyword in question_lower for keyword in risk_keywords):
        print("Question classified as: RISK")
        return "risk"

    print("Question classified as: GENERAL")
    return "general"


if __name__ == "__main__":
    # Test our classifier
    test_questions = [
        "What is the penalty for late payment?",
        "What are my obligations if I want to terminate?",
        "How long does confidentiality last?",
        "What is the governing law?"
    ]

    print("TESTING QUESTION CLASSIFIER")
    print("="*50)

    for question in test_questions:
        question_type = classify_question(question)
        template = get_prompt_template(question_type)
        print(f"Q: {question}")
        print(f"Template: {question_type}")
        print(f"Template variables: {template.input_variables}")
        print("-"*50)
