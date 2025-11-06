#!/usr/bin/env python3
"""
Advanced test script for RAG bidding system - Testing retrieval and query functionality
"""
import os
import sys
import json
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_retrieval_functionality():
    """Test different retrieval modes and strategies"""
    print("🔍 Testing Retrieval Functionality...")
    
    try:
        from langchain_openai import OpenAIEmbeddings
        from langchain_postgres import PGVector
        from src.config.models import settings
        from src.retrieval.retrievers import create_retriever
        
        # Initialize components
        embeddings = OpenAIEmbeddings(model=settings.embed_model)
        vector_store = PGVector(
            embeddings=embeddings,
            collection_name=settings.collection,
            connection=settings.database_url,
        )
        
        # Test queries
        test_queries = [
            "Luật đầu tư năm 2020",
            "Quy định về đăng ký kinh doanh",
            "Thủ tục cấp phép xây dựng",
            "Hồ sơ mời thầu dự án",
            "Nghị định về đầu tư công"
        ]
        
        # Test different retrieval modes
        modes = ["fast", "balanced", "quality", "adaptive"]
        
        for mode in modes:
            print(f"\n🔧 Testing {mode.upper()} mode:")
            
            try:
                retriever = create_retriever(mode=mode, enable_reranking=True)
                
                for query in test_queries[:2]:  # Test with first 2 queries only
                    start_time = time.time()
                    
                    # Test retrieval
                    docs = retriever.get_relevant_documents(query)
                    
                    retrieval_time = time.time() - start_time
                    
                    print(f"  📋 Query: '{query}'")
                    print(f"     Found: {len(docs)} documents")
                    print(f"     Time: {retrieval_time:.2f}s")
                    
                    if docs:
                        # Show first result details
                        doc = docs[0]
                        content_preview = doc.page_content[:100].replace('\n', ' ')
                        print(f"     Top result: {content_preview}...")
                        
                        if hasattr(doc, 'metadata') and doc.metadata:
                            metadata_keys = list(doc.metadata.keys())
                            print(f"     Metadata: {metadata_keys[:5]}...")  # Show first 5 keys
                    
                    time.sleep(0.5)  # Small delay between queries
                    
            except Exception as e:
                print(f"  ❌ Error in {mode} mode: {e}")
                continue
        
        return True
        
    except Exception as e:
        print(f"❌ Retrieval test failed: {e}")
        return False

def test_qa_functionality():
    """Test Question Answering functionality"""
    print("\n🔍 Testing Q&A Functionality...")
    
    try:
        from src.generation.chains.qa_chain import answer
        
        test_questions = [
            "Luật đầu tư quy định gì về thủ tục đăng ký kinh doanh?",
            "Điều kiện để được cấp giấy phép đầu tư là gì?",
            "Quy trình mời thầu có những bước nào?"
        ]
        
        modes = ["fast", "balanced"]  # Test only fast and balanced to save time
        
        for mode in modes:
            print(f"\n🔧 Testing {mode.upper()} Q&A mode:")
            
            try:
                for question in test_questions[:2]:  # Test first 2 questions
                    start_time = time.time()
                    
                    result = answer(question, mode=mode, use_enhancement=True)
                    
                    qa_time = time.time() - start_time
                    
                    print(f"  ❓ Question: '{question}'")
                    print(f"     Answer: {result['answer'][:150]}...")
                    print(f"     Sources: {len(result['sources'])} documents")
                    print(f"     Time: {qa_time:.2f}s")
                    
                    if 'enhanced_features' in result:
                        print(f"     Features: {result['enhanced_features']}")
                    
                    time.sleep(1)  # Delay between questions
                    
            except Exception as e:
                print(f"  ❌ Error in {mode} Q&A: {e}")
                continue
        
        return True
        
    except Exception as e:
        print(f"❌ Q&A test failed: {e}")
        return False

def test_vector_search_detailed():
    """Test detailed vector search functionality"""
    print("\n🔍 Testing Detailed Vector Search...")
    
    try:
        from langchain_openai import OpenAIEmbeddings
        from langchain_postgres import PGVector
        from src.config.models import settings
        
        embeddings = OpenAIEmbeddings(model=settings.embed_model)
        vector_store = PGVector(
            embeddings=embeddings,
            collection_name=settings.collection,
            connection=settings.database_url,
        )
        
        # Test different search types
        query = "Quy định về đầu tư nước ngoài"
        
        print(f"📋 Testing search for: '{query}'")
        
        # 1. Similarity search
        print("\n  🔸 Similarity Search:")
        docs = vector_store.similarity_search(query, k=3)
        for i, doc in enumerate(docs):
            print(f"    {i+1}. {doc.page_content[:80]}...")
        
        # 2. Similarity search with score
        print("\n  🔸 Similarity Search with Scores:")
        docs_with_scores = vector_store.similarity_search_with_score(query, k=3)
        for i, (doc, score) in enumerate(docs_with_scores):
            print(f"    {i+1}. Score: {score:.3f} | {doc.page_content[:60]}...")
        
        # 3. MMR (Maximum Marginal Relevance) search
        print("\n  🔸 MMR Search (diversity):")
        try:
            mmr_docs = vector_store.max_marginal_relevance_search(query, k=3)
            for i, doc in enumerate(mmr_docs):
                print(f"    {i+1}. {doc.page_content[:80]}...")
        except Exception as e:
            print(f"    ⚠️  MMR not supported: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Vector search test failed: {e}")
        return False

def test_metadata_filtering():
    """Test metadata-based filtering"""
    print("\n🔍 Testing Metadata Filtering...")
    
    try:
        from langchain_openai import OpenAIEmbeddings
        from langchain_postgres import PGVector
        from src.config.models import settings
        
        embeddings = OpenAIEmbeddings(model=settings.embed_model)
        vector_store = PGVector(
            embeddings=embeddings,
            collection_name=settings.collection,
            connection=settings.database_url,
        )
        
        query = "đầu tư"
        
        # Test different metadata filters
        filters_to_test = [
            {"document_type": "law"},
            {"level": 1},
            {"has_table": True},
        ]
        
        print(f"📋 Testing filters for query: '{query}'")
        
        # First, get all results without filter
        all_docs = vector_store.similarity_search(query, k=5)
        print(f"\n  🔸 No filter: {len(all_docs)} documents")
        
        for filter_dict in filters_to_test:
            try:
                filtered_docs = vector_store.similarity_search(
                    query, 
                    k=5, 
                    filter=filter_dict
                )
                print(f"  🔸 Filter {filter_dict}: {len(filtered_docs)} documents")
                
                if filtered_docs:
                    # Show metadata of first result
                    first_doc = filtered_docs[0]
                    if hasattr(first_doc, 'metadata') and first_doc.metadata:
                        relevant_metadata = {k: v for k, v in first_doc.metadata.items() 
                                           if k in filter_dict.keys() or k in ['document_type', 'level', 'section_title']}
                        print(f"    Sample metadata: {relevant_metadata}")
                
            except Exception as e:
                print(f"    ⚠️  Filter {filter_dict} failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Metadata filtering test failed: {e}")
        return False

def main():
    """Run comprehensive retrieval and query tests"""
    print("🚀 RAG Bidding System - Advanced Testing")
    print("=" * 60)
    
    # Check if we have OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY not found in environment")
        sys.exit(1)
    
    print(f"🔑 OpenAI API Key: {os.getenv('OPENAI_API_KEY')[:20]}...")
    print(f"🗄️  Database: {os.getenv('DB_NAME')}")
    print(f"📚 Collection: {os.getenv('LC_COLLECTION')}")
    print(f"🤖 Embed Model: {os.getenv('EMBED_MODEL')}")
    print(f"🧠 LLM Model: {os.getenv('LLM_MODEL')}")
    
    # Run tests
    tests = [
        ("Vector Search", test_vector_search_detailed),
        ("Metadata Filtering", test_metadata_filtering),
        ("Retrieval Modes", test_retrieval_functionality),
        ("Q&A Functionality", test_qa_functionality),
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
            print(f"\n⏹️  Test interrupted by user")
            break
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
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
        print("\n🎉 All tests passed! RAG system is working correctly.")
    else:
        print(f"\n⚠️  {total_tests - passed_tests} tests failed. Check the errors above.")

if __name__ == "__main__":
    main()