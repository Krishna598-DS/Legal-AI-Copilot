"""Conversational RAG with query rewriting and short-term memory."""

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from src.llm.formatting import format_docs
from src.logging_config import logger
from src.safety.prompts import with_safety_preamble

CONTEXTUALIZE_SYSTEM = """You are a query rewriter for a legal document Q&A system.

Rewrite the follow-up question so it is fully standalone without chat history.
If it is already standalone, return it unchanged.
Do not answer the question — only rewrite it.
Do not add legal advice.
"""

ANSWER_SYSTEM = with_safety_preamble(
    """You are a senior legal document analyst providing Legal Information only.

Answer questions about legal documents accurately and clearly.

STRICT RULES:
1. Answer ONLY using the provided document context
2. If information is not in the context, say: "This information is not found in the provided document."
3. Cite the section or page your answer comes from (use [Source N] when available)
4. You may reference earlier answers naturally
5. Provide Legal Information about what the document says — never Legal Advice
6. If the user asks what they should do, explain you cannot advise and recommend a licensed lawyer

CONTEXT FROM DOCUMENT:
{context}
"""
)


def create_conversational_chain(retriever, llm):
    """Return (contextualize_chain, answer_chain)."""
    contextualize_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", CONTEXTUALIZE_SYSTEM),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    answer_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", ANSWER_SYSTEM),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    contextualize_chain = contextualize_prompt | llm | StrOutputParser()
    answer_chain = answer_prompt | llm | StrOutputParser()
    return contextualize_chain, answer_chain


class ConversationalRAG:
    """Stateful conversational RAG (per-document instance)."""

    def __init__(self, retriever, llm, memory_window: int = 6):
        self.retriever = retriever
        self.llm = llm
        self.chat_history: list = []
        self.memory_window = memory_window
        self.contextualize_chain, self.answer_chain = create_conversational_chain(
            retriever, llm
        )
        logger.debug("ConversationalRAG initialized")

    def ask(self, question: str) -> dict:
        if self.chat_history:
            standalone = self.contextualize_chain.invoke(
                {"input": question, "chat_history": self.chat_history}
            )
        else:
            standalone = question

        docs = self.retriever.invoke(standalone)
        context = format_docs(docs)
        answer = self.answer_chain.invoke(
            {
                "input": standalone,
                "context": context,
                "chat_history": self.chat_history,
            }
        )

        self.chat_history.append(HumanMessage(content=question))
        self.chat_history.append(AIMessage(content=answer))
        if len(self.chat_history) > self.memory_window:
            self.chat_history = self.chat_history[-self.memory_window :]

        return {
            "question": question,
            "standalone_question": standalone,
            "answer": answer,
            "history_length": len(self.chat_history),
        }

    def reset_memory(self) -> None:
        self.chat_history = []
