import os
import time
from typing import Dict, Literal
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
from src.retrieval.answer_cache import get_answer_cache
from src.retrieval.semantic_cache_v2 import get_semantic_cache_v2
from src.config.models import settings, apply_preset


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


def is_casual_query(question: str) -> tuple[bool, str | None]:
    """
    Detect if query is casual/conversational (not requiring RAG).

    Returns:
        Tuple of (is_casual, direct_response)
        - is_casual: True if query doesn't need RAG
        - direct_response: Pre-defined response if casual, None otherwise
    """
    question_lower = question.lower().strip()
    question_stripped = question.strip()

    # Very short queries (likely greetings)
    if len(question_stripped) < 5:
        return (
            True,
            "Xin chào! 👋 Tôi là trợ lý pháp luật đấu thầu. Bạn có câu hỏi gì về đấu thầu không?",
        )

    # Greeting patterns
    greetings = [
        "xin chào",
        "chào bạn",
        "chào",
        "hello",
        "hi",
        "hey",
        "alo",
        "ê",
        "ơi",
        "bạn ơi",
        "chào buổi sáng",
        "chào buổi tối",
        "good morning",
        "good afternoon",
        "good evening",
    ]

    for greeting in greetings:
        if (
            question_lower == greeting
            or question_lower.startswith(greeting + " ")
            or question_lower.startswith(greeting + ",")
        ):
            return (
                True,
                "Xin chào! 👋 Tôi là trợ lý chuyên về pháp luật đấu thầu Việt Nam. Bạn cần hỏi gì về đấu thầu, tôi sẵn sàng hỗ trợ!",
            )

    # Thank you patterns
    thanks = ["cảm ơn", "cám ơn", "thank", "thanks", "tks", "ok cảm ơn", "ok thanks"]
    for thank in thanks:
        if thank in question_lower:
            return (
                True,
                "Không có gì! 😊 Nếu bạn có thêm câu hỏi về đấu thầu, cứ hỏi nhé!",
            )

    # Goodbye patterns
    goodbyes = ["tạm biệt", "bye", "goodbye", "hẹn gặp lại", "chào nhé"]
    for goodbye in goodbyes:
        if goodbye in question_lower:
            return True, "Tạm biệt! 👋 Hẹn gặp lại bạn. Chúc bạn một ngày tốt lành!"

    # Identity questions
    identity_patterns = [
        "bạn là ai",
        "bạn là gì",
        "tên bạn là gì",
        "ai tạo ra bạn",
        "bạn có thể làm gì",
        "bạn làm được gì",
        "giới thiệu bản thân",
        "what are you",
        "who are you",
        "what can you do",
    ]
    for pattern in identity_patterns:
        if pattern in question_lower:
            return True, (
                "Tôi là trợ lý AI chuyên về pháp luật đấu thầu Việt Nam. 📚\n\n"
                "Tôi có thể giúp bạn:\n"
                "- Tra cứu quy định trong Luật Đấu thầu, Nghị định, Thông tư\n"
                "- Giải đáp thắc mắc về quy trình đấu thầu\n"
                "- Tìm hiểu điều kiện, tiêu chuẩn cho nhà thầu\n"
                "- Hướng dẫn về hồ sơ mời thầu, đánh giá thầu\n\n"
                "Hãy đặt câu hỏi cụ thể về đấu thầu để tôi hỗ trợ bạn!"
            )

    # Simple yes/no or confirmation
    simple_responses = [
        "ok",
        "ừ",
        "uh",
        "được",
        "rồi",
        "vâng",
        "dạ",
        "yes",
        "no",
        "không",
    ]
    if question_lower in simple_responses:
        return True, "Bạn có câu hỏi gì khác về đấu thầu không? Tôi sẵn sàng hỗ trợ!"

    return False, None


# Prompt will be created dynamically in answer() function
# prompt = ChatPromptTemplate.from_messages(
#     [("system", SYSTEM_PROMPT), ("user", USER_TEMPLATE)]
# )


def _get_document_statuses(docs) -> Dict[str, str]:
    """
    Get document statuses from documents table.

    This enriches retrieved documents with their validity status
    (active/expired/superseded) from the documents table.

    Args:
        docs: List of LangChain Documents with document_id in metadata

    Returns:
        Dict mapping document_id to status string
    """
    from src.models.base import SessionLocal
    from src.models.documents import Document
    import logging

    logger = logging.getLogger(__name__)
    statuses = {}

    # Extract unique document_ids from retrieved docs
    doc_ids = set()
    for d in docs:
        doc_id = d.metadata.get("document_id")
        if doc_id:
            doc_ids.add(doc_id)

    if not doc_ids:
        return statuses

    # Query documents table for statuses
    try:
        db = SessionLocal()
        try:
            # Query by document_id field (not UUID id)
            documents = (
                db.query(Document.document_id, Document.status)
                .filter(Document.document_id.in_(list(doc_ids)))
                .all()
            )

            for doc in documents:
                statuses[doc.document_id] = doc.status or "active"

            # Log if any expired documents found
            expired_docs = [d for d, s in statuses.items() if s != "active"]
            if expired_docs:
                logger.info(
                    f"📋 Found {len(expired_docs)} non-active documents in results: {expired_docs}"
                )

        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Failed to fetch document statuses: {e}")

    return statuses


def fmt_docs(docs):
    lines = []
    for i, d in enumerate(docs, 1):
        lines.append(f"[#{i}]\n{d.page_content}\n")
    return "\n".join(lines)


def format_document_reference(doc, index: int, doc_status: str | None = None) -> str:
    """
    Format document reference với thông tin chi tiết.

    Args:
        doc: LangChain Document
        index: Reference number
        doc_status: Status from documents table (active/expired/superseded)
    """
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

    # Add status warning if document is not active
    status_warning = ""
    if doc_status and doc_status != "active":
        status_labels = {
            "expired": "⚠️ HẾT HIỆU LỰC",
            "superseded": "⚠️ ĐÃ ĐƯỢC THAY THẾ",
            "archived": "📁 ĐÃ LƯU TRỮ",
            "draft": "📝 BẢN NHÁP",
        }
        status_warning = f" {status_labels.get(doc_status, f'⚠️ {doc_status.upper()}')}"

    return (
        f"[#{index}] {hierarchy}{doc_type_str}{status_warning}\n    📄 {content_preview}\n    🔗 {source_info}"
        if source_info
        else f"[#{index}] {hierarchy}{doc_type_str}{status_warning}\n    📄 {content_preview}"
    )


def answer(
    question: str,
    mode: str | None = None,
    reranker_type: Literal["bge", "openai"] = "bge",  # Default: OpenAI (API-based)
    use_cache: bool = True,  # 🆕 Enable/disable answer cache
    original_query: (
        str | None
    ) = None,  # 🆕 Original query for cache key (without context)
) -> Dict:
    """
    Answer a question using RAG pipeline.

    Args:
        question: User's question (may include conversation context)
        mode: RAG mode (fast/balanced/quality/adaptive)
        reranker_type: Reranker to use ("bge" or "openai")
        use_cache: Enable answer caching (default: True)
        original_query: Original user query for cache key (without conversation context).
                       If None, uses question as cache key.

    Returns:
        Dict with answer, sources, and metadata
    """
    # 🆕 Use original_query for cache operations if provided
    cache_key_query = original_query or question
    import logging

    logger = logging.getLogger(__name__)
    start_time = time.time()

    # ✅ EARLY EXIT: Check if query is casual/conversational (no RAG needed)
    is_casual, direct_response = is_casual_query(question)
    if is_casual:
        logger.info(
            f"💬 Casual query detected, skipping RAG pipeline: '{question[:50]}...'"
        )
        return {
            "answer": direct_response,
            "sources": [],
            "detailed_sources": [],
            "source_documents_raw": [],
            "adaptive_retrieval": {
                "mode": "casual",
                "docs_retrieved": 0,
                "enhancement_enabled": False,
                "has_expired_docs": False,
                "skipped_rag": True,
            },
            "enhanced_features": [],
            "document_statuses": {},
        }

    # ✅ CHECK ANSWER CACHE (before running expensive RAG pipeline)
    # 🆕 Use cache_key_query (original query without context) for cache lookup
    answer_cache = get_answer_cache()
    if use_cache:
        cached_result = answer_cache.get(cache_key_query)
        if cached_result:
            processing_time_ms = int((time.time() - start_time) * 1000)
            logger.info(
                f"⚡ Answer cache HIT - returning cached result in {processing_time_ms}ms"
            )

            # Reconstruct sources in proper format for API response
            # The API expects List[str] for 'sources' field
            cached_sources_raw = cached_result.get("sources", [])

            # Convert cached sources (list of dicts) to simple string format
            src_lines = []
            for i, src in enumerate(cached_sources_raw, 1):
                if isinstance(src, dict):
                    doc_name = src.get("document_name", "Tài liệu")
                    section = src.get("section", "")
                    if section:
                        src_lines.append(f"[#{i}] {section} - {doc_name}")
                    else:
                        src_lines.append(f"[#{i}] {doc_name}")
                else:
                    # Already a string
                    src_lines.append(src if isinstance(src, str) else str(src))

            # Return cached result with updated timing and proper format
            return {
                "answer": cached_result.get("answer", ""),
                "sources": src_lines,  # List[str] for API compatibility
                "detailed_sources": cached_result.get("detailed_sources", []),
                "source_documents_raw": cached_sources_raw,  # Original format for frontend
                "adaptive_retrieval": {
                    "mode": cached_result.get("rag_mode", "unknown"),
                    "docs_retrieved": len(cached_sources_raw),
                    "enhancement_enabled": True,
                    "has_expired_docs": False,
                    "from_cache": True,
                    "cache_hit_time_ms": processing_time_ms,
                    "original_processing_time_ms": cached_result.get(
                        "processing_time_ms", 0
                    ),
                },
                "enhanced_features": ["Answer Cache HIT"],
                "document_statuses": {},
            }
        else:
            # 🆕 SEMANTIC CACHE V2: Hybrid Cosine + BGE reranker
            semantic_cache = get_semantic_cache_v2()
            similar_match = semantic_cache.find_similar(cache_key_query)

            if similar_match:
                # Found a semantically similar query - get its cached answer
                similar_cached = answer_cache.get(similar_match.original_query)

                if similar_cached:
                    processing_time_ms = int((time.time() - start_time) * 1000)
                    logger.info(
                        f"🔍 Semantic cache V2 HIT - bge_score={similar_match.bge_score:.4f}, "
                        f"cosine={similar_match.cosine_similarity:.4f}, "
                        f"original='{similar_match.original_query[:50]}...'"
                    )

                    # Reconstruct sources in proper format
                    cached_sources_raw = similar_cached.get("sources", [])
                    src_lines = []
                    for i, src in enumerate(cached_sources_raw, 1):
                        if isinstance(src, dict):
                            doc_name = src.get("document_name", "Tài liệu")
                            section = src.get("section", "")
                            if section:
                                src_lines.append(f"[#{i}] {section} - {doc_name}")
                            else:
                                src_lines.append(f"[#{i}] {doc_name}")
                        else:
                            src_lines.append(src if isinstance(src, str) else str(src))

                    return {
                        "answer": similar_cached.get("answer", ""),
                        "sources": src_lines,
                        "detailed_sources": similar_cached.get("detailed_sources", []),
                        "source_documents_raw": cached_sources_raw,
                        "adaptive_retrieval": {
                            "mode": similar_cached.get("rag_mode", "unknown"),
                            "docs_retrieved": len(cached_sources_raw),
                            "enhancement_enabled": True,
                            "has_expired_docs": False,
                            "from_cache": True,
                            "cache_type": "semantic_v2",
                            "bge_score": round(similar_match.bge_score, 4),
                            "cosine_similarity": round(similar_match.cosine_similarity, 4),
                            "similar_query": similar_match.original_query[:100],
                            "cache_hit_time_ms": processing_time_ms,
                            "original_processing_time_ms": similar_cached.get(
                                "processing_time_ms", 0
                            ),
                        },
                        "enhanced_features": [
                            f"Semantic Cache V2 HIT (bge={similar_match.bge_score:.2%})"
                        ],
                        "document_statuses": {},
                    }

            logger.info(
                f"❌ Answer cache MISS (exact + semantic) - running full RAG pipeline"
            )

    selected_mode = mode or settings.rag_mode or "balanced"
    apply_preset(selected_mode)

    # ✅ Create retriever dynamically based on selected_mode and reranker_type
    enable_reranking = settings.enable_reranking and selected_mode != "fast"
    retriever = create_retriever(
        mode=selected_mode,
        enable_reranking=enable_reranking,
        reranker_type=reranker_type,
    )

    # ✅ Select prompt based on query complexity
    use_detailed_prompt = is_complex_query(question)
    system_prompt = SYSTEM_PROMPT_DETAILED if use_detailed_prompt else SYSTEM_PROMPT

    if use_detailed_prompt:
        logger.info(
            "🔍 Complex query detected → Using DETAILED prompt for comprehensive analysis"
        )

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

    # Enrich source documents with status from documents table
    doc_statuses = _get_document_statuses(result["source_documents"])

    # Tạo detailed source references
    src_lines = []
    detailed_sources = []
    has_expired_docs = False

    for i, d in enumerate(result["source_documents"], 1):
        # Get status from documents table (default to "active" if not found)
        doc_id = d.metadata.get("document_id", "")
        doc_status = doc_statuses.get(doc_id, "active")

        if doc_status != "active":
            has_expired_docs = True

        # Tạo reference chi tiết với status
        detailed_ref = format_document_reference(d, i, doc_status)
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

        # Add status to simple source line if not active
        status_suffix = f" [{doc_status.upper()}]" if doc_status != "active" else ""
        src_lines.append(f"[#{i}] {hierarchy} - {doc_title}{status_suffix}")

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

    # Add warning about expired documents in answer if needed
    answer_text = result["answer"].strip()
    if has_expired_docs:
        answer_text += "\n\n⚠️ **Lưu ý**: Một số tài liệu tham khảo đã hết hiệu lực hoặc được thay thế. Vui lòng kiểm tra văn bản hiện hành."

    # Build final result
    final_result = {
        "answer": answer_text,
        "sources": src_lines,
        "detailed_sources": detailed_sources,
        "source_documents_raw": [
            {
                "document_id": d.metadata.get("document_id", ""),
                "document_name": d.metadata.get(
                    "document_name", d.metadata.get("title", "Tài liệu")
                ),
                "chunk_id": d.metadata.get("chunk_id", ""),
                "content": d.page_content[:500],  # First 500 chars as citation
                "hierarchy": d.metadata.get("hierarchy", []),
                "section_title": d.metadata.get("section_title", ""),
                "document_type": d.metadata.get("document_type", ""),
                "category": d.metadata.get("category", ""),
                "dieu": d.metadata.get("dieu"),
                "khoan": d.metadata.get("khoan"),
                "diem": d.metadata.get("diem"),
                "status": doc_statuses.get(d.metadata.get("document_id", ""), "active"),
            }
            for d in result["source_documents"]
        ],
        "adaptive_retrieval": {
            "mode": selected_mode,
            "docs_retrieved": len(result["source_documents"]),
            "enhancement_enabled": selected_mode != "fast",
            "has_expired_docs": has_expired_docs,
            "from_cache": False,
        },
        "enhanced_features": enhanced_features,
        "document_statuses": doc_statuses,
    }

    # ✅ CACHE THE RESULT (for future requests with same query)
    # 🆕 Use cache_key_query (original query without context) for cache storage
    processing_time_ms = int((time.time() - start_time) * 1000)
    if use_cache:
        try:
            # Prepare sources for caching (simplified format)
            cache_sources = [
                {
                    "document_id": d.metadata.get("document_id", ""),
                    "document_name": d.metadata.get(
                        "document_name", d.metadata.get("title", "")
                    ),
                    "chunk_id": d.metadata.get("chunk_id", ""),
                    "citation_text": d.page_content[:500],
                    "section": d.metadata.get("section_title", ""),
                }
                for d in result["source_documents"]
            ]
            answer_cache.set(
                query=cache_key_query,  # 🆕 Use original query for cache key
                answer=answer_text,
                sources=cache_sources,
                rag_mode=selected_mode,
                processing_time_ms=processing_time_ms,
            )

            # 🆕 Store embedding for semantic cache V2 (Hybrid Cosine + BGE)
            try:
                semantic_cache = get_semantic_cache_v2()
                semantic_cache.store_embedding(
                    query=cache_key_query,  # 🆕 Use original query for semantic cache
                    answer_cache_key=f"rag:answer:{cache_key_query}",  # Reference to answer cache
                )
            except Exception as e:
                logger.debug(f"⚠️ Failed to store semantic embedding: {e}")

            logger.info(
                f"📦 Answer cached for future requests (processing_time={processing_time_ms}ms, cache_key='{cache_key_query[:50]}...')"
            )
        except Exception as e:
            logger.warning(f"⚠️ Failed to cache answer: {e}")

    return final_result
