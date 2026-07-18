"""LCEL RAG chain used by the evaluation harness."""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough

from src.llm.formatting import format_docs
from src.llm.prompt_templates import get_prompt_template


def build_rag_chain(retriever, llm, question_type: str = "general"):
    """Build a non-conversational RAG chain for offline evaluation."""
    prompt = get_prompt_template(question_type)
    return (
        RunnableParallel(
            {
                "context": retriever | format_docs,
                "question": RunnablePassthrough(),
            }
        )
        | prompt
        | llm
        | StrOutputParser()
    )
