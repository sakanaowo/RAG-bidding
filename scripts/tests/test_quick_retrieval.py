#!/usr/bin/env python3
"""
Quick test for retrieval functionality after fixing filter issue
"""
import os
from dotenv import load_dotenv

load_dotenv()

def test_retrieval_quick():
    """Quick test for retrieval modes"""
    print("🔍 Quick Retrieval Test (after filter fix)")
    
    try:
        from src.retrieval.retrievers import create_retriever
        
        test_query = "Luật đầu tư"
        modes = ["fast", "balanced"]
        
        for mode in modes:
            print(f"\n🔧 Testing {mode.upper()} mode:")
            try:
                retriever = create_retriever(mode=mode, enable_reranking=False)  # Disable reranking for speed
                docs = retriever.invoke(test_query)  # Use invoke instead of deprecated method
                
                print(f"  📋 Query: '{test_query}'")
                print(f"     Found: {len(docs)} documents")
                
                if docs:
                    doc = docs[0]
                    content_preview = doc.page_content[:100].replace('\n', ' ')
                    print(f"     Top result: {content_preview}...")
                    
                    if hasattr(doc, 'metadata') and doc.metadata:
                        print(f"     Document type: {doc.metadata.get('document_type', 'unknown')}")
                        print(f"     Section: {doc.metadata.get('section_title', 'unknown')}")
                else:
                    print("     ⚠️  No documents found")
                    
            except Exception as e:
                print(f"  ❌ Error in {mode} mode: {e}")
                import traceback
                traceback.print_exc()
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_qa_quick():
    """Quick test for Q&A"""
    print("\n🔍 Quick Q&A Test")
    
    try:
        from src.generation.chains.qa_chain import answer
        
        question = "Luật đầu tư quy định gì?"
        
        print(f"❓ Question: '{question}'")
        
        result = answer(question, mode="fast", use_enhancement=False)
        
        print(f"✅ Answer: {result['answer'][:200]}...")
        print(f"📚 Sources: {len(result['sources'])} documents")
        
        if result['sources']:
            print("📋 Source preview:")
            for i, source in enumerate(result['sources'][:2]):
                print(f"  {i+1}. {source[:80]}...")
        
        return True
        
    except Exception as e:    
        print(f"❌ Q&A test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Quick RAG Test")
    print("=" * 40)
    
    retrieval_ok = test_retrieval_quick()
    qa_ok = test_qa_quick()
    
    print("\n" + "=" * 40)
    print("📊 RESULTS:")
    print(f"   Retrieval: {'✅ PASS' if retrieval_ok else '❌ FAIL'}")
    print(f"   Q&A: {'✅ PASS' if qa_ok else '❌ FAIL'}")
    
    if retrieval_ok and qa_ok:
        print("\n🎉 Quick test passed! System is working.")
    else:
        print("\n⚠️  Some issues detected.")