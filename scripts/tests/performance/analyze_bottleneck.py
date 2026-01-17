#!/usr/bin/env python3
"""
Bottleneck Analysis Script
Phân tích nguyên nhân BE xử lý chậm mặc dù đã tăng connection pool
"""

import sys
import os
import time
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, List
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

API_BASE_URL = "http://localhost:8000"
API_PREFIX = "/api"


def print_header(title: str):
    print(f"\n{'='*70}")
    print(f"🔍 {title}")
    print(f"{'='*70}")


async def check_server_status():
    """Kiểm tra status server"""
    print_header("SERVER STATUS CHECK")

    endpoints = [
        ("/health", "Health Check"),
        ("/", "Root"),
    ]

    async with aiohttp.ClientSession() as session:
        for endpoint, name in endpoints:
            try:
                start = time.time()
                async with session.get(f"{API_BASE_URL}{endpoint}", timeout=5) as resp:
                    elapsed = (time.time() - start) * 1000
                    print(f"  ✅ {name}: {resp.status} ({elapsed:.0f}ms)")
            except Exception as e:
                print(f"  ❌ {name}: {e}")


async def test_single_request_latency(email: str, password: str):
    """Test latency của từng loại request khi server idle"""
    print_header("SINGLE REQUEST LATENCY (Server Idle)")

    async with aiohttp.ClientSession() as session:
        # Login first
        print("\n  📍 Login...")
        start = time.time()
        async with session.post(
            f"{API_BASE_URL}{API_PREFIX}/auth/login",
            json={"email": email, "password": password},
        ) as resp:
            login_time = (time.time() - start) * 1000
            if resp.status != 200:
                print(f"  ❌ Login failed: {await resp.text()}")
                return
            data = await resp.json()
            token = data["tokens"]["access_token"]
            print(f"  ✅ Login: {login_time:.0f}ms")

        headers = {"Authorization": f"Bearer {token}"}

        # Test each endpoint 3 times
        endpoints = [
            ("GET", f"{API_PREFIX}/auth/me", None, "User Profile"),
            ("GET", f"{API_PREFIX}/conversations", None, "List Conversations"),
            (
                "POST",
                f"{API_PREFIX}/conversations",
                {"title": "Test", "rag_mode": "fast"},
                "Create Conversation",
            ),
        ]

        print("\n  📍 Endpoint Latencies (3 runs each):")

        for method, path, body, name in endpoints:
            times = []
            for _ in range(3):
                start = time.time()
                if method == "GET":
                    async with session.get(
                        f"{API_BASE_URL}{path}", headers=headers
                    ) as resp:
                        elapsed = (time.time() - start) * 1000
                        times.append(elapsed)
                else:
                    async with session.post(
                        f"{API_BASE_URL}{path}", json=body, headers=headers
                    ) as resp:
                        elapsed = (time.time() - start) * 1000
                        times.append(elapsed)
                        if name == "Create Conversation" and resp.status == 201:
                            data = await resp.json()
                            conv_id = data.get("id")

            avg = sum(times) / len(times)
            print(
                f"     • {name:<25}: {avg:>8.0f}ms (min: {min(times):.0f}, max: {max(times):.0f})"
            )

        # Test RAG query
        if conv_id:
            print("\n  📍 RAG Query Latencies (3 runs, mode=fast):")
            queries = [
                "chỉ định thầu",
                "hồ sơ mời thầu",
                "quy trình đấu thầu",
            ]

            for query in queries:
                start = time.time()
                async with session.post(
                    f"{API_BASE_URL}{API_PREFIX}/conversations/{conv_id}/messages",
                    json={"content": query},
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    elapsed = (time.time() - start) * 1000
                    if resp.status == 200:
                        data = await resp.json()
                        server_time = data.get("assistant_message", {}).get(
                            "processing_time_ms", 0
                        )
                        print(
                            f'     • "{query[:20]}..." : {elapsed:>8.0f}ms (server reported: {server_time}ms)'
                        )
                    else:
                        print(f'     • "{query[:20]}..." : ❌ {resp.status}')


async def test_concurrent_latency(
    email_prefix: str, password: str, num_concurrent: int = 10
):
    """Test latency khi có nhiều requests đồng thời"""
    print_header(f"CONCURRENT REQUEST LATENCY ({num_concurrent} simultaneous)")

    async def single_login(session, email):
        start = time.time()
        try:
            async with session.post(
                f"{API_BASE_URL}{API_PREFIX}/auth/login",
                json={"email": email, "password": password},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                elapsed = (time.time() - start) * 1000
                return elapsed, resp.status == 200
        except Exception as e:
            return (time.time() - start) * 1000, False

    async with aiohttp.ClientSession() as session:
        # Concurrent logins
        print(f"\n  📍 {num_concurrent} Concurrent Logins:")

        emails = [f"test{i:03d}@testmail.com" for i in range(1, num_concurrent + 1)]

        start_all = time.time()
        tasks = [single_login(session, email) for email in emails]
        results = await asyncio.gather(*tasks)
        total_time = (time.time() - start_all) * 1000

        times = [r[0] for r in results]
        successes = sum(1 for r in results if r[1])

        print(f"     • Success: {successes}/{num_concurrent}")
        print(f"     • Total wall time: {total_time:.0f}ms")
        print(f"     • Avg per request: {sum(times)/len(times):.0f}ms")
        print(f"     • Min: {min(times):.0f}ms, Max: {max(times):.0f}ms")
        print(f"     • Throughput: {num_concurrent / (total_time/1000):.1f} req/s")


async def analyze_rag_bottleneck(email: str, password: str):
    """Phân tích bottleneck trong RAG pipeline"""
    print_header("RAG PIPELINE BOTTLENECK ANALYSIS")

    print(
        """
  🔍 RAG Pipeline có các bước sau:
     1. Query Enhancement (Multi-Query, HyDE, etc.)
     2. Vector Search (pgvector similarity search)
     3. Reranking (BGE-reranker or OpenAI)
     4. LLM Generation (OpenAI API call)
  
  ⚠️  Các bottleneck tiềm năng:
     • OpenAI API latency (network + processing): 2-10s
     • Vector search với large dataset: 100-500ms
     • Reranking với many chunks: 500-2000ms
     • Database connection pool: nếu quá tải
  
  💡 Tăng DB pool KHÔNG giúp nếu bottleneck là OpenAI API!
     OpenAI có rate limits và latency riêng.
"""
    )


async def check_database_stats():
    """Kiểm tra database connection stats (yêu cầu endpoint riêng)"""
    print_header("DATABASE CONNECTION ANALYSIS")

    print(
        """
  📊 Để kiểm tra database connections, cần:
  
  1. Kiểm tra PostgreSQL:
     psql -c "SELECT count(*) FROM pg_stat_activity;"
     psql -c "SELECT state, count(*) FROM pg_stat_activity GROUP BY state;"
  
  2. Kiểm tra SQLAlchemy pool:
     Thêm endpoint /debug/pool-status vào API để xem pool stats
  
  3. Kiểm tra max_connections trong PostgreSQL:
     psql -c "SHOW max_connections;"
  
  ⚠️  Nếu pool_size=100 nhưng PostgreSQL max_connections=100,
     thì chỉ có thể có 100 connections tối đa!
"""
    )


def print_recommendations():
    """In các đề xuất khắc phục"""
    print_header("RECOMMENDATIONS")

    print(
        """
  🎯 CÁC NGUYÊN NHÂN CHÍNH GÂY CHẬM:
  
  1. ⏱️  OPENAI API LATENCY (Bottleneck chính cho RAG)
     • Mỗi RAG query cần 1-3 OpenAI API calls
     • OpenAI latency: 2-10s mỗi call
     • Concurrent OpenAI calls có thể bị rate limited
     
     ✅ Giải pháp:
     • Dùng mode "fast" thay vì "balanced/quality" 
     • Implement caching cho similar queries
     • Dùng streaming response
     • Dùng local LLM (Ollama) cho testing
  
  2. 🔄 CONNECTION POOL CONFIGURATION
     • pool_size=100, max_overflow=20 → 120 max connections
     • PostgreSQL max_connections=200 → OK
     • Nhưng mỗi RAG request giữ connection lâu (chờ OpenAI)
     
     ✅ Giải pháp:
     • Tăng pool_timeout từ 30 → 60
     • Giảm số concurrent users trong test
     • Dùng async database sessions
  
  3. 🔍 VECTOR SEARCH PERFORMANCE
     • pgvector cần optimize cho large datasets
     
     ✅ Giải pháp:
     • Thêm HNSW index cho vector column
     • Tăng work_mem cho PostgreSQL
     • Kiểm tra EXPLAIN ANALYZE của queries
  
  4. 🎭 FASTAPI WORKERS
     • Default chỉ có 1 worker
     
     ✅ Giải pháp:
     • Chạy với nhiều workers: uvicorn --workers 4
     • Hoặc dùng gunicorn với uvicorn workers
  
  📝 QUICK TEST:
     # Test với ít users hơn và mode fast
     python test_authenticated_users.py --users 10 --requests 5 --batch-size 5
     
     # So sánh với mode balanced
     # Nếu mode fast nhanh hơn nhiều → bottleneck là OpenAI
"""
    )


async def main():
    print("\n" + "=" * 70)
    print("🔬 BACKEND PERFORMANCE BOTTLENECK ANALYZER")
    print("=" * 70)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Target: {API_BASE_URL}")

    # Check server
    await check_server_status()

    # Test single request latency
    await test_single_request_latency("test001@testmail.com", "TestPass123!")

    # Test concurrent latency
    await test_concurrent_latency("test", "TestPass123!", num_concurrent=20)

    # Analyze RAG
    await analyze_rag_bottleneck("test001@testmail.com", "TestPass123!")

    # Database stats
    await check_database_stats()

    # Recommendations
    print_recommendations()

    print("\n" + "=" * 70)
    print("✅ Analysis complete!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
