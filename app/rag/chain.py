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
from app.rag.prompts import SYSTEM_PROMPT, USER_TEMPLATE
from app.rag.retriever import retriever
from app.rag.adaptive_retriever import adaptive_retriever, explain_retrieval_strategy
from app.core.config import settings, apply_preset


model = ChatOpenAI(model=settings.llm_model, temperature=0)

prompt = ChatPromptTemplate.from_messages(
    [("system", SYSTEM_PROMPT), ("user", USER_TEMPLATE)]
)


def fmt_docs(docs):
    lines = []
    for i, d in enumerate(docs, 1):
        lines.append(f"[#{i}]\n{d.page_content}\n")
    return "\n".join(lines)


rag_core = (
    {"context": retriever | RunnableLambda(fmt_docs), "question": RunnablePassthrough()}
    | prompt
    | model
    | StrOutputParser()
)


chain = RunnableParallel(answer=rag_core, source_documents=retriever)


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


def answer(question: str, mode: str | None = None) -> Dict:
    selected_mode = mode or settings.rag_mode or "balanced"
    apply_preset(selected_mode)

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

    analysis = adaptive_retriever.analyze_question_complexity(question)
    strategy_info = explain_retrieval_strategy(question, analysis)

    return {
        "answer": result["answer"].strip()
        + "\n\nNguồn:\n"
        + "\n".join(detailed_sources),
        "sources": src_lines,
        "detailed_sources": detailed_sources,
        "phase1_mode": selected_mode,
        "adaptive_retrieval": {
            "strategy": strategy_info,
            "complexity": analysis["complexity"],
            "k_used": analysis["suggested_k"],
            "docs_retrieved": len(result["source_documents"]),
            "word_count": analysis["word_count"],
        },
        "enhanced_features": [
            "✅ Adaptive Retrieval (Dynamic K)",
            "✅ Question Complexity Analysis",
            "✅ Enhanced Configuration Presets",
            "⏳ Query Enhancement (Phase 2)",
            "⏳ Document Reranking (Phase 2)",
        ],
    }
