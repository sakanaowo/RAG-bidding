"""
Enhanced RAG Chain với Query Enhancement và Reranking
Demonstration implementation cho các cải thiện được đề xuất
"""

from typing import Dict, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnableParallel
from src.generation.prompts.qa_prompts import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    QUERY_ENHANCER_PROMPT,
    DOC_RANKING_PROMPT,
    FACT_CHECK_PROMPT,
)
from src.retrieval.retrievers.base_retriever import retriever
from config.models import settings


# Models cho các giai đoạn khác nhau
main_model = ChatOpenAI(model=settings.llm_model, temperature=0)
enhancer_model = ChatOpenAI(
    model=settings.llm_model, temperature=0.3
)  # Creativity cho query expansion
ranker_model = ChatOpenAI(model=settings.llm_model, temperature=0)


def enhance_query(question: str) -> str:
    """
    Cải thiện câu hỏi để tăng hiệu quả retrieval
    """
    enhance_prompt = ChatPromptTemplate.from_template(QUERY_ENHANCER_PROMPT)
    enhancer = enhance_prompt | enhancer_model | StrOutputParser()

    enhanced_result = enhancer.invoke({"original_query": question})

    # Extract enhanced query từ kết quả (simple parsing)
    lines = enhanced_result.split("\n")
    for line in lines:
        if line.startswith("1)"):
            return line.split(":", 1)[1].strip() if ":" in line else question

    return question  # Fallback to original


def rerank_documents(documents: List, question: str) -> List:
    """
    Rerank documents dựa trên relevance với câu hỏi cụ thể
    """
    if len(documents) <= 2:
        return documents

    docs_text = ""
    for i, doc in enumerate(documents):
        docs_text += f"[Doc {i+1}] {doc.page_content[:500]}...\n\n"

    rank_prompt = ChatPromptTemplate.from_template(DOC_RANKING_PROMPT)
    ranker = rank_prompt | ranker_model | StrOutputParser()

    try:
        ranking_result = ranker.invoke({"query": question, "documents": docs_text})

        # Simple parsing để extract order (implementation cần tinh chỉnh)
        # Ở đây ta giả sử LLM trả về thứ tự, hoặc có thể implement logic phức tạp hơn
        return documents  # Placeholder - cần implement proper parsing

    except Exception:
        return documents  # Fallback nếu reranking fail


def validate_answer(answer: str, documents: List) -> Dict:
    """
    Kiểm tra chất lượng câu trả lời
    """
    docs_text = "\n".join([doc.page_content for doc in documents[:3]])

    fact_check_prompt = ChatPromptTemplate.from_template(FACT_CHECK_PROMPT)
    checker = fact_check_prompt | main_model | StrOutputParser()

    try:
        validation = checker.invoke(
            {"generated_answer": answer, "source_documents": docs_text}
        )

        return {
            "validation": validation,
            "has_citations": "[#" in answer,
            "answer_length": len(answer.split()),
        }
    except Exception:
        return {"validation": "Could not validate", "has_citations": "[#" in answer}


def fmt_docs(docs):
    """Format documents cho context"""
    lines = []
    for i, d in enumerate(docs, 1):
        lines.append(f"[#{i}]\n{d.page_content}\n")
    return "\n".join(lines)


# Enhanced RAG Chain
def enhanced_retrieval_chain(question: str):
    """
    Enhanced retrieval với query enhancement và reranking
    """
    # Step 1: Enhance query
    enhanced_question = enhance_query(question)

    # Step 2: Retrieve với enhanced query
    raw_docs = retriever.invoke(enhanced_question)

    # Step 3: Rerank documents
    reranked_docs = rerank_documents(raw_docs, question)

    return reranked_docs


# Main enhanced chain
prompt = ChatPromptTemplate.from_messages(
    [("system", SYSTEM_PROMPT), ("user", USER_TEMPLATE)]
)

enhanced_rag_core = (
    {
        "context": RunnableLambda(enhanced_retrieval_chain) | RunnableLambda(fmt_docs),
        "question": lambda x: x,
    }
    | prompt
    | main_model
    | StrOutputParser()
)

enhanced_chain = RunnableParallel(
    answer=enhanced_rag_core, source_documents=RunnableLambda(enhanced_retrieval_chain)
)


def enhanced_answer(question: str) -> Dict:
    """
    Enhanced answer function với validation
    """
    result = enhanced_chain.invoke(question)

    # Validate answer quality
    validation_info = validate_answer(result["answer"], result["source_documents"])

    # Format sources
    src_lines = []
    for i, d in enumerate(result["source_documents"], 1):
        path = d.metadata.get("path") or d.metadata.get("source") or str(d.metadata)
        src_lines.append(f"[#{i}] {path}")

    return {
        "answer": result["answer"].strip() + "\n\nNguồn:\n" + "\n".join(src_lines),
        "sources": src_lines,
        "validation": validation_info,
        "enhanced": True,  # Flag để phân biệt với chain thường
    }


# Utility function để so sánh performance
def compare_chains(question: str) -> Dict:
    """
    So sánh kết quả giữa chain thường và enhanced chain
    """
    from src.generation.chains.qa_chain import answer as basic_answer

    basic_result = basic_answer(question)
    enhanced_result = enhanced_answer(question)

    return {
        "question": question,
        "basic": basic_result,
        "enhanced": enhanced_result,
        "comparison": {
            "basic_length": len(basic_result["answer"]),
            "enhanced_length": len(enhanced_result["answer"]),
            "basic_citations": basic_result["answer"].count("[#"),
            "enhanced_citations": enhanced_result["answer"].count("[#"),
        },
    }
