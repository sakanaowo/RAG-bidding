#!/usr/bin/env python3
"""
Simple test script to verify database connection and basic query functionality
"""
import os
import sys
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_database_connection():
    """Test PostgreSQL database connection"""
    print("🔍 Testing database connection...")
    
    try:
        import psycopg
        dsn = os.getenv('DATABASE_URL').replace('postgresql+psycopg', 'postgresql')
        print(f"📡 Connecting to: {dsn.replace(os.getenv('DB_PASSWORD', ''), '***')}")
        
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                # Test basic queries
                cur.execute('SELECT version();')
                version = cur.fetchone()[0]
                print(f"✅ PostgreSQL Version: {version[:50]}...")
                
                # Check extensions
                cur.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
                vector_ext = cur.fetchone()
                if vector_ext:
                    print(f"✅ pgvector extension: {vector_ext[1]} (version {vector_ext[2]})")
                else:
                    print("❌ pgvector extension not found")
                
                # Check tables
                cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
                tables = [row[0] for row in cur.fetchall()]
                print(f"📊 Tables found: {', '.join(tables)}")
                
                # Check data counts
                cur.execute('SELECT COUNT(*) FROM langchain_pg_collection;')
                collections = cur.fetchone()[0]
                cur.execute('SELECT COUNT(*) FROM langchain_pg_embedding;')
                embeddings = cur.fetchone()[0]
                
                print(f"📈 Collections: {collections}")
                print(f"📈 Embeddings: {embeddings}")
                
                return True
                
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_langchain_connection():
    """Test LangChain PGVector connection"""
    print("\n🔍 Testing LangChain PGVector connection...")
    
    try:
        from langchain_openai import OpenAIEmbeddings
        from langchain_postgres import PGVector
        from src.config.models import settings
        
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
        test_query = "Luật về đầu tư"
        
        # Get similar documents
        docs = vector_store.similarity_search(
            query=test_query,
            k=3
        )
        
        print(f"✅ Found {len(docs)} similar documents for query: '{test_query}'")
        
        if docs:
            for i, doc in enumerate(docs):
                print(f"  {i+1}. {doc.page_content[:100]}...")
                if doc.metadata:
                    print(f"     Metadata: {list(doc.metadata.keys())}")
        
        return True
        
    except Exception as e:
        print(f"❌ LangChain connection failed: {e}")
        return False

def test_api_health():
    """Test API health endpoint (if server is running)"""  
    print("\n🔍 Testing API health endpoint...")
    
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API health check passed: {data}")
            return True
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("⚠️  API server not running (connection refused)")
        return False
    except Exception as e:
        print(f"❌ API health check error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 RAG Bidding System - Database & API Test")
    print("=" * 50)
    
    # Test 1: Database connection
    db_ok = test_database_connection()
    
    # Test 2: LangChain connection (only if DB is OK)
    langchain_ok = False
    if db_ok:
        langchain_ok = test_langchain_connection()
    
    # Test 3: API health (optional)
    api_ok = test_api_health()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY:")
    print(f"   Database Connection: {'✅ PASS' if db_ok else '❌ FAIL'}")
    print(f"   LangChain Vector Store: {'✅ PASS' if langchain_ok else '❌ FAIL'}")
    print(f"   API Health: {'✅ PASS' if api_ok else '⚠️  SKIP (server not running)'}")
    
    if db_ok and langchain_ok:
        print("\n🎉 System is ready for testing!")
        if not api_ok:
            print("💡 Start the server with: ./start_server.sh")
    else:
        print("\n⚠️  Some components need attention before testing")
        sys.exit(1)

if __name__ == "__main__":
    main()