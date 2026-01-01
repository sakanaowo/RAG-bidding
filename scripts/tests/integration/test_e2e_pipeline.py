#!/usr/bin/env python3
"""
End-to-End Testing for RAG System
Tests complete pipeline: Query → Retrieval → Context Formatting → Generation
"""
import sys
from pathlib import Path
from typing import List, Dict, Any
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_postgres import PGVector
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.config.models import settings
from src.generation.formatters.context_formatter import format_context_with_hierarchy


class RAGPipeline:
    """Complete RAG pipeline for testing."""

    def __init__(self):
        """Initialize RAG components."""
        # Vector store
        self.embeddings = OpenAIEmbeddings(model=settings.embed_model)
        self.vector_store = PGVector(
            embeddings=self.embeddings,
            collection_name=settings.collection,
            connection=settings.database_url,
            use_jsonb=True,
        )

        # LLM
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
        )

        # Prompt template
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """Bạn là trợ lý AI chuyên về luật đấu thầu Việt Nam. 
Nhiệm vụ của bạn là trả lời câu hỏi dựa trên các văn bản pháp luật được cung cấp.

Hướng dẫn:
- Trích dẫn cụ thể Điều, Khoản khi trả lời
- Trả lời ngắn gọn, chính xác
- Nếu thông tin không có trong văn bản, hãy nói rõ
- Sử dụng thông tin về hierarchy để hiểu ngữ cảnh""",
                ),
                ("user", "{context}\n\nQuestion: {question}\n\nAnswer:"),
            ]
        )

        # Chain
        self.chain = self.prompt | self.llm | StrOutputParser()

    def retrieve(
        self,
        query: str,
        k: int = 5,
        document_types: List[str] = None,
        levels: List[str] = None,
    ) -> List[Document]:
        """
        Retrieve relevant documents.

        Args:
            query: User question
            k: Number of documents to retrieve
            document_types: Filter by document types
            levels: Filter by hierarchy levels

        Returns:
            Retrieved documents
        """
        # Build filter
        filter_dict = {}
        if document_types:
            if len(document_types) == 1:
                filter_dict["document_type"] = document_types[0]
            else:
                filter_dict["document_type"] = {"$in": document_types}

        if levels:
            if len(levels) == 1:
                filter_dict["level"] = levels[0]
            else:
                filter_dict["level"] = {"$in": levels}

        # Retrieve
        docs = self.vector_store.similarity_search(
            query, k=k, filter=filter_dict if filter_dict else None
        )

        return docs

    def generate(self, query: str, docs: List[Document]) -> str:
        """
        Generate answer from retrieved documents.

        Args:
            query: User question
            docs: Retrieved documents

        Returns:
            Generated answer
        """
        # Format context
        context = format_context_with_hierarchy(
            docs,
            query=query,
            include_instructions=False,  # Instructions in system prompt
        )

        # Generate
        answer = self.chain.invoke({"context": context, "question": query})

        return answer

    def run(
        self,
        query: str,
        k: int = 5,
        document_types: List[str] = None,
        levels: List[str] = None,
        show_context: bool = False,
    ) -> Dict[str, Any]:
        """
        Run complete RAG pipeline.

        Args:
            query: User question
            k: Number of documents to retrieve
            document_types: Filter by document types
            levels: Filter by hierarchy levels
            show_context: Print formatted context

        Returns:
            Result dict with query, docs, answer, timing
        """
        start_time = time.time()

        # 1. Retrieve
        retrieve_start = time.time()
        docs = self.retrieve(query, k=k, document_types=document_types, levels=levels)
        retrieve_time = time.time() - retrieve_start

        # 2. Generate
        generate_start = time.time()
        answer = self.generate(query, docs)
        generate_time = time.time() - generate_start

        total_time = time.time() - start_time

        # Build result
        result = {
            "query": query,
            "docs_count": len(docs),
            "docs": docs,
            "answer": answer,
            "timing": {
                "retrieve_ms": round(retrieve_time * 1000, 2),
                "generate_ms": round(generate_time * 1000, 2),
                "total_ms": round(total_time * 1000, 2),
            },
        }

        # Show context if requested
        if show_context:
            context = format_context_with_hierarchy(docs, query=query)
            result["context"] = context

        return result


def run_e2e_tests():
    """Run end-to-end tests."""
    print("=" * 80)
    print("END-TO-END RAG PIPELINE TESTING")
    print("=" * 80)
    print()

    # Initialize pipeline
    print("🔧 Initializing RAG pipeline...")
    pipeline = RAGPipeline()
    print("✓ Pipeline ready\n")

    # Test cases
    test_cases = [
        {
            "name": "Basic Query - Law Documents",
            "query": "Điều kiện tham gia đấu thầu là gì?",
            "k": 3,
            "document_types": ["law"],
            "levels": None,
        },
        {
            "name": "Decree Documents - Specific Level",
            "query": "Hồ sơ mời thầu phải bao gồm những nội dung gì?",
            "k": 3,
            "document_types": ["decree"],
            "levels": ["khoan", "dieu"],
        },
        {
            "name": "Bidding Templates - Forms",
            "query": "Mẫu hợp đồng xây dựng có những nội dung chính nào?",
            "k": 3,
            "document_types": ["bidding"],
            "levels": None,
        },
        {
            "name": "Mixed Document Types",
            "query": "Quy trình đánh giá hồ sơ dự thầu như thế nào?",
            "k": 5,
            "document_types": ["law", "decree"],
            "levels": None,
        },
        {
            "name": "No Filters - All Documents",
            "query": "Thời hạn bảo lãnh dự thầu là bao lâu?",
            "k": 5,
            "document_types": None,
            "levels": None,
        },
    ]

    results = []

    for i, test in enumerate(test_cases, 1):
        print(f"{'='*80}")
        print(f"TEST {i}/{len(test_cases)}: {test['name']}")
        print(f"{'='*80}")
        print(f"Query: {test['query']}")
        print(f"Filters: types={test['document_types']}, levels={test['levels']}")
        print()

        # Run pipeline
        result = pipeline.run(
            query=test["query"],
            k=test["k"],
            document_types=test["document_types"],
            levels=test["levels"],
            show_context=False,  # Don't print full context (too long)
        )

        # Print results
        print(f"📊 Retrieved: {result['docs_count']} documents")
        print(f"⏱️  Timing:")
        print(f"   - Retrieval: {result['timing']['retrieve_ms']}ms")
        print(f"   - Generation: {result['timing']['generate_ms']}ms")
        print(f"   - Total: {result['timing']['total_ms']}ms")
        print()

        # Print retrieved doc types
        doc_types = {}
        for doc in result["docs"]:
            dtype = doc.metadata.get("document_type", "unknown")
            doc_types[dtype] = doc_types.get(dtype, 0) + 1
        print(f"📄 Document Types: {dict(doc_types)}")

        # Print answer
        print(f"\n💬 ANSWER:")
        print("-" * 80)
        print(result["answer"])
        print("-" * 80)
        print()

        results.append(result)

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    avg_retrieve = sum(r["timing"]["retrieve_ms"] for r in results) / len(results)
    avg_generate = sum(r["timing"]["generate_ms"] for r in results) / len(results)
    avg_total = sum(r["timing"]["total_ms"] for r in results) / len(results)

    print(f"Total tests: {len(results)}")
    print(f"\nAverage timing:")
    print(f"  - Retrieval: {avg_retrieve:.2f}ms")
    print(f"  - Generation: {avg_generate:.2f}ms")
    print(f"  - Total: {avg_total:.2f}ms")

    print(f"\nPerformance:")
    if avg_total < 2000:
        print("  ✅ Excellent (<2s per query)")
    elif avg_total < 5000:
        print("  ✓ Good (<5s per query)")
    else:
        print("  ⚠️  Needs optimization (>5s per query)")

    print("\n" + "=" * 80)
    print("✅ END-TO-END TESTING COMPLETE!")
    print("=" * 80)


if __name__ == "__main__":
    run_e2e_tests()
