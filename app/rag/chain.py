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


def answer(question: str, mode: str | None = None) -> Dict:
    selected_mode = mode or settings.rag_mode or "balanced"
    apply_preset(selected_mode)

    result = chain.invoke(question)
    src_lines = []
    for i, d in enumerate(result["source_documents"], 1):
        path = d.metadata.get("path") or d.metadata.get("source") or str(d.metadata)
        src_lines.append(f"[#{i}] {path}")

    analysis = adaptive_retriever.analyze_question_complexity(question)
    strategy_info = explain_retrieval_strategy(question, analysis)

    return {
        "answer": result["answer"].strip() + "\n\nNguồn:\n" + "\n".join(src_lines),
        "sources": src_lines,
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
