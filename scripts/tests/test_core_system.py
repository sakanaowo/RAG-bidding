#!/usr/bin/env python3
"""
Database and core system test suite
"""
import os
import sys
import time
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DatabaseTester:
    def __init__(self):
        self.results = {}

    def test_database_connection(self) -> bool:
        """Test PostgreSQL database connection"""
        print("🔍 Testing database connection...")

        try:
            import psycopg

            dsn = os.getenv("DATABASE_URL").replace("postgresql+psycopg", "postgresql")
            db_name = os.getenv("DB_NAME", "unknown")
            print(f"📡 Connecting to database: {db_name}")

            with psycopg.connect(dsn) as conn:
                with conn.cursor() as cur:
                    # Test basic queries
                    cur.execute("SELECT version();")
                    version = cur.fetchone()[0]
                    print(f"✅ PostgreSQL: {version[:60]}...")

                    # Check extensions
                    cur.execute(
                        "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
                    )
                    vector_ext = cur.fetchone()
                    if vector_ext:
                        print(
                            f"✅ pgvector extension: {vector_ext[0]} v{vector_ext[1]}"
                        )
                    else:
                        print("❌ pgvector extension not found")
                        return False

                    # Check tables
                    cur.execute(
                        "SELECT tablename FROM pg_tables WHERE schemaname = 'public';"
                    )
                    tables = [row[0] for row in cur.fetchall()]
                    expected_tables = [
                        "langchain_pg_collection",
                        "langchain_pg_embedding",
                    ]

                    print(f"📊 Tables found: {', '.join(tables)}")

                    for table in expected_tables:
                        if table not in tables:
                            print(f"❌ Missing table: {table}")
                            return False

                    # Check data counts
                    cur.execute("SELECT COUNT(*) FROM langchain_pg_collection;")
                    collections = cur.fetchone()[0]
                    cur.execute("SELECT COUNT(*) FROM langchain_pg_embedding;")
                    embeddings = cur.fetchone()[0]

                    print(f"📈 Collections: {collections}")
                    print(f"📈 Embeddings: {embeddings}")

                    if collections == 0 or embeddings == 0:
                        print("⚠️  Warning: No data found in database")
                        return False

                    return True

        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False

    def test_langchain_connection(self) -> bool:
        """Test LangChain PGVector connection"""
        print("\n🔍 Testing LangChain PGVector connection...")

        try:
            from langchain_openai import OpenAIEmbeddings
            from langchain_postgres import PGVector
            from src.config.models import settings

            # Check OpenAI API key
            if not os.getenv("OPENAI_API_KEY"):
                print("❌ OPENAI_API_KEY not found in environment")
                return False

            # Initialize embeddings
            embeddings = OpenAIEmbeddings(model=settings.embed_model)
            print(f"✅ OpenAI Embeddings initialized: {settings.embed_model}")

            # Initialize vector store
            vector_store = PGVector(
                embeddings=embeddings,
                collection_name=settings.collection,
                connection=settings.database_url,
            )
            print(f"✅ PGVector store initialized: collection '{settings.collection}'")

            # Test similarity search
            print("\n🔍 Testing similarity search...")
            test_queries = [
                "Luật về đầu tư",
                "Quy định đăng ký kinh doanh",
                "Thủ tục mời thầu",
            ]

            successful_searches = 0

            for query in test_queries:
                try:
                    docs = vector_store.similarity_search(query, k=3)
                    print(f"  📋 Query: '{query}' → {len(docs)} documents")

                    if docs:
                        doc = docs[0]
                        content_preview = (
                            doc.page_content[:80].replace("\n", " ").strip()
                        )
                        metadata = doc.metadata or {}
                        doc_type = metadata.get("document_type", "unknown")
                        section = metadata.get("section_title", "unknown")

                        print(f"     📄 Top result: {content_preview}...")
                        print(f"     🏷️  Type: {doc_type} | Section: {section}")
                        successful_searches += 1
                    else:
                        print(f"     ⚠️  No documents found for '{query}'")

                except Exception as e:
                    print(f"     ❌ Search failed for '{query}': {e}")

            return successful_searches > 0

        except Exception as e:
            print(f"❌ LangChain connection failed: {e}")
            return False

    def test_retrieval_system(self) -> bool:
        """Test retrieval system functionality"""
        print("\n🔍 Testing retrieval system...")

        try:
            from src.retrieval.retrievers import create_retriever

            test_cases = [
                {"mode": "fast", "query": "Luật đầu tư"},
                {"mode": "balanced", "query": "Quy định về đăng ký kinh doanh"},
            ]

            successful_retrievals = 0

            for case in test_cases:
                try:
                    print(f"  🔧 Testing {case['mode'].upper()} mode...")

                    retriever = create_retriever(
                        mode=case["mode"], enable_reranking=False
                    )
                    docs = retriever.invoke(case["query"])

                    print(f"     📋 Query: '{case['query']}'")
                    print(f"     📄 Documents found: {len(docs)}")

                    if docs:
                        doc = docs[0]
                        content_preview = (
                            doc.page_content[:100].replace("\n", " ").strip()
                        )
                        metadata = doc.metadata or {}

                        print(f"     📝 Top result: {content_preview}...")
                        print(f"     🏷️  Metadata keys: {list(metadata.keys())[:5]}")
                        successful_retrievals += 1
                    else:
                        print(f"     ⚠️  No documents found")

                except Exception as e:
                    print(f"     ❌ Retrieval failed for {case['mode']}: {e}")

            return successful_retrievals > 0

        except Exception as e:
            print(f"❌ Retrieval system test failed: {e}")
            return False

    def test_qa_system(self) -> bool:
        """Test Q&A system functionality"""
        print("\n🔍 Testing Q&A system...")

        try:
            from src.generation.chains.qa_chain import answer

            test_questions = [
                "Luật đầu tư quy định gì?",
                "Thủ tục đăng ký kinh doanh như thế nào?",
            ]

            successful_answers = 0

            for question in test_questions:
                try:
                    print(f"  ❓ Question: '{question}'")

                    start_time = time.time()
                    result = answer(question, mode="fast", use_enhancement=False)
                    qa_time = time.time() - start_time

                    answer_text = result.get("answer", "")
                    sources = result.get("sources", [])

                    print(f"     💡 Answer: {answer_text[:100]}...")
                    print(f"     📚 Sources: {len(sources)} documents")
                    print(f"     ⏱️  Time: {qa_time:.2f}s")

                    if len(sources) > 0 and "không biết" not in answer_text.lower():
                        successful_answers += 1
                    else:
                        print(f"     ⚠️  No relevant answer found")

                except Exception as e:
                    print(f"     ❌ Q&A failed for '{question}': {e}")

            return successful_answers > 0

        except Exception as e:
            print(f"❌ Q&A system test failed: {e}")
            return False

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all system tests"""
        print("🚀 RAG Bidding System - Core System Tests")
        print("=" * 60)

        # Environment check
        print("🔧 Environment Check:")
        print(f"   Database: {os.getenv('DB_NAME', 'NOT_SET')}")
        print(f"   Collection: {os.getenv('LC_COLLECTION', 'NOT_SET')}")
        print(f"   Embed Model: {os.getenv('EMBED_MODEL', 'NOT_SET')}")
        print(f"   LLM Model: {os.getenv('LLM_MODEL', 'NOT_SET')}")
        print(
            f"   OpenAI Key: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Missing'}"
        )

        if not os.getenv("OPENAI_API_KEY"):
            print("\n❌ OPENAI_API_KEY is required for testing")
            return {}

        # Run tests
        tests = [
            ("Database Connection", self.test_database_connection),
            ("LangChain Vector Store", self.test_langchain_connection),
            ("Retrieval System", self.test_retrieval_system),
            ("Q&A System", self.test_qa_system),
        ]

        results = {}

        for test_name, test_func in tests:
            print(f"\n{'='*60}")
            try:
                start_time = time.time()
                success = test_func()
                test_time = time.time() - start_time
                results[test_name] = {"success": success, "time": test_time}
            except KeyboardInterrupt:
                print(f"\n⏹️  Tests interrupted by user")
                break
            except Exception as e:
                print(f"\n❌ Test '{test_name}' crashed: {e}")
                results[test_name] = {"success": False, "time": 0, "error": str(e)}

        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY:")

        total_tests = len(results)
        passed_tests = sum(1 for r in results.values() if r["success"])

        for test_name, result in results.items():
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            time_str = f"({result['time']:.1f}s)" if result["time"] > 0 else ""
            print(f"   {test_name}: {status} {time_str}")

            if not result["success"] and "error" in result:
                print(f"      Error: {result['error']}")

        print(f"\n🎯 Overall: {passed_tests}/{total_tests} tests passed")

        if passed_tests == total_tests:
            print("\n🎉 All core tests passed! System is ready for API testing.")
            print(
                "💡 Next step: Start the server with 'python scripts/tests/test_api_server.py'"
            )
        else:
            print(
                f"\n⚠️  {total_tests - passed_tests} tests failed. Fix the issues before proceeding."
            )

        return results


def main():
    """Main test runner"""
    tester = DatabaseTester()
    results = tester.run_all_tests()

    # Exit with appropriate code
    if all(r["success"] for r in results.values()):
        exit(0)
    else:
        exit(1)


if __name__ == "__main__":
    main()
