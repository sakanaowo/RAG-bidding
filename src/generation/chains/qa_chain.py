import os
from typing import Dict
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import (
    RunnablePassthrough,
    RunnableLambda,
    RunnableParallel,
)
from src.generation.prompts.qa_prompts import (
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_DETAILED,
    USER_TEMPLATE,
)
from src.retrieval.retrievers import create_retriever
from config.models import settings, apply_preset


model = ChatOpenAI(model=settings.llm_model, temperature=0)


def is_complex_query(question: str) -> bool:
    """
    Detect if query requires detailed analysis.
    
    Complex query indicators:
    - Contains keywords: phân tích, so sánh, tổng hợp, chi tiết, toàn bộ
    - Multiple aspects (contains "và", "bao gồm")
    - Long query (>100 chars)
    """
    question_lower = question.lower()
    
    # Keywords requiring detailed response
    detailed_keywords = [
        "phân tích",
        "so sánh", 
        "tổng hợp",
        "chi tiết",
        "toàn bộ",
        "phân biệt",
        "khác nhau",
        "giống nhau",
        "ưu nhược điểm",
        "ưu điểm",
        "nhược điểm",
    ]
    
    # Check keywords
    if any(keyword in question_lower for keyword in detailed_keywords):
        return True
    
    # Check multiple aspects
    if ("bao gồm" in question_lower or "và" in question_lower) and len(question) > 80:
        return True
    
    # Check length
    if len(question) > 150:
        return True
    
    return False


# Prompt will be created dynamically in answer() function
# prompt = ChatPromptTemplate.from_messages(
#     [("system", SYSTEM_PROMPT), ("user", USER_TEMPLATE)]
# )


def fmt_docs(docs):
    lines = []
    for i, d in enumerate(docs, 1):
        lines.append(f"[#{i}]\n{d.page_content}\n")
    return "\n".join(lines)


# ❌ REMOVED: Global retriever initialization causes all requests to use same mode
# retriever = create_retriever(mode="balanced")
# rag_chain = (
#     {"context": retriever | fmt_docs, "question": RunnablePassthrough()}
#     | prompt
#     | model
#     | StrOutputParser()
# )
# chain = RunnableParallel(answer=rag_chain, source_documents=retriever)

# ✅ NOW: Create retriever dynamically per request in answer() function


def format_document_reference(doc, index: int) -> str:
    """Format document reference với thông tin chi tiết."""
    meta = doc.metadata

    # Lấy thông tin cơ bản
    title = meta.get("title", "Tài liệu")
    doc_type = meta.get("document_type", "")

    # Thông tin vị trí trong tài liệu
    hierarchy_parts = []

    # Thêm chương nếu có
    if meta.get("chuong"):
        hierarchy_parts.append(f"Chương {meta['chuong']}")

    # Thêm điều
    if meta.get("dieu"):
        hierarchy_parts.append(f"Điều {meta['dieu']}")

    # Thêm khoản nếu có
    if meta.get("khoan"):
        hierarchy_parts.append(f"Khoản {meta['khoan']}")

    # Thêm điểm nếu có
    if meta.get("diem"):
        hierarchy_parts.append(f"Điểm {meta['diem']}")

    # Tạo hierarchy string
    hierarchy = " → ".join(hierarchy_parts) if hierarchy_parts else "Nội dung chung"

    # URL nguồn nếu có
    url = meta.get("url", "")
    source_info = f"({url})" if url else ""

    # Preview nội dung
    content_preview = doc.page_content[:100].replace("\n", " ").strip()
    if len(doc.page_content) > 100:
        content_preview += "..."

    # Format final reference
    if doc_type:
        doc_type_str = f" - {doc_type}"
    else:
        doc_type_str = ""

    return (
        f"[#{index}] {hierarchy}{doc_type_str}\n    📄 {content_preview}\n    🔗 {source_info}"
        if source_info
        else f"[#{index}] {hierarchy}{doc_type_str}\n    📄 {content_preview}"
    )


def answer(
    question: str, mode: str | None = None, use_enhancement: bool = True
) -> Dict:
    selected_mode = mode or settings.rag_mode or "balanced"
    apply_preset(selected_mode)

    # ✅ Create retriever dynamically based on selected_mode
    enable_reranking = settings.enable_reranking and selected_mode != "fast"
    retriever = create_retriever(mode=selected_mode, enable_reranking=enable_reranking)

    # ✅ Select prompt based on query complexity
    use_detailed_prompt = is_complex_query(question)
    system_prompt = SYSTEM_PROMPT_DETAILED if use_detailed_prompt else SYSTEM_PROMPT
    
    import logging
    logger = logging.getLogger(__name__)
    if use_detailed_prompt:
        logger.info("🔍 Complex query detected → Using DETAILED prompt for comprehensive analysis")
    
    prompt = ChatPromptTemplate.from_messages(
        [("system", system_prompt), ("user", USER_TEMPLATE)]
    )

    # Build chain dynamically with the correct retriever and prompt
    rag_chain = (
        {"context": retriever | fmt_docs, "question": RunnablePassthrough()}
        | prompt
        | model
        | StrOutputParser()
    )
    
    chain = RunnableParallel(answer=rag_chain, source_documents=retriever)
    
    result = chain.invoke(question)

    # Tạo detailed source references
    src_lines = []
    detailed_sources = []

    for i, d in enumerate(result["source_documents"], 1):
        # Tạo reference chi tiết
        detailed_ref = format_document_reference(d, i)
        detailed_sources.append(detailed_ref)

        # Tạo source line đơn giản cho backward compatibility
        meta = d.metadata
        hierarchy_parts = []

        if meta.get("dieu"):
            hierarchy_parts.append(f"Điều {meta['dieu']}")
        if meta.get("khoan"):
            hierarchy_parts.append(f"Khoản {meta['khoan']}")
        if meta.get("diem"):
            hierarchy_parts.append(f"Điểm {meta['diem']}")

        hierarchy = " ".join(hierarchy_parts) if hierarchy_parts else "Văn bản"
        doc_title = meta.get("title", "Tài liệu pháp luật")

        src_lines.append(f"[#{i}] {hierarchy} - {doc_title}")

    # Build enhanced features list based on actual mode
    enhanced_features = []

    # Query Enhancement strategies (actual ones used)
    if selected_mode == "fast":
        # Fast mode: no enhancement
        pass
    elif selected_mode == "balanced":
        enhanced_features.append("Query Enhancement (Multi-Query, Step-Back)")
    elif selected_mode == "quality":
        enhanced_features.append(
            "Query Enhancement (Multi-Query, HyDE, Step-Back, Decomposition)"
        )
    elif selected_mode == "adaptive":
        enhanced_features.append("Query Enhancement (Multi-Query, Step-Back)")

    # RAG-Fusion (only quality mode)
    if selected_mode == "quality":
        enhanced_features.append("RAG-Fusion with RRF")

    # Adaptive K (only adaptive mode)
    if selected_mode == "adaptive":
        enhanced_features.append("Adaptive K Selection")

    # Document Reranking (all modes except fast)
    if selected_mode != "fast" and settings.enable_reranking:
        enhanced_features.append("Document Reranking (BGE)")

    return {
        "answer": result["answer"].strip()
        + "\n\nNguồn:\n"
        + "\n".join(detailed_sources),
        "sources": src_lines,
        "detailed_sources": detailed_sources,
        "adaptive_retrieval": {
            "mode": selected_mode,
            "docs_retrieved": len(result["source_documents"]),
            "enhancement_enabled": selected_mode != "fast",
        },
        "enhanced_features": enhanced_features,
    }
