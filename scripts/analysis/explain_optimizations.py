#!/usr/bin/env python3
"""
PostgreSQL + pgvector Index Tuning and Connection Pooling
Demonstrates optimization techniques for vector search performance.
"""
import sys
from pathlib import Path
import time
from typing import List, Dict, Any
import psycopg
from psycopg.rows import dict_row

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from src.config.models import settings


class IndexTuningGuide:
    """
    Guide for pgvector index optimization.

    pgvector supports 2 index types:
    1. IVFFlat (Inverted File with Flat compression)
       - Approximate nearest neighbor search
       - Fast but less accurate than exact search
       - Good for: Large datasets (>10k vectors)

    2. HNSW (Hierarchical Navigable Small World)
       - Graph-based index
       - More accurate, faster queries, slower builds
       - Good for: Production use, high QPS
    """

    def __init__(self, database_url: str):
        # Remove SQLAlchemy prefix if present
        self.database_url = database_url.replace(
            "postgresql+psycopg://", "postgresql://"
        )

    def analyze_current_indexes(self):
        """Check current indexes on embedding table."""
        print("=" * 80)
        print("CURRENT INDEX ANALYSIS")
        print("=" * 80)

        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                # Check table size
                cur.execute(
                    """
                    SELECT 
                        pg_size_pretty(pg_total_relation_size('langchain_pg_embedding')) as total_size,
                        pg_size_pretty(pg_relation_size('langchain_pg_embedding')) as table_size,
                        pg_size_pretty(pg_total_relation_size('langchain_pg_embedding') - 
                                     pg_relation_size('langchain_pg_embedding')) as indexes_size,
                        (SELECT COUNT(*) FROM langchain_pg_embedding) as row_count
                """
                )
                table_stats = cur.fetchone()

                print("\n📊 Table Statistics:")
                print(f"   Total size: {table_stats['total_size']}")
                print(f"   Table size: {table_stats['table_size']}")
                print(f"   Indexes size: {table_stats['indexes_size']}")
                print(f"   Row count: {table_stats['row_count']:,}")

                # Check existing indexes
                cur.execute(
                    """
                    SELECT 
                        indexname,
                        indexdef,
                        pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
                    FROM pg_indexes 
                    WHERE tablename = 'langchain_pg_embedding'
                    ORDER BY indexname
                """
                )
                indexes = cur.fetchall()

                print("\n📑 Current Indexes:")
                for idx in indexes:
                    print(f"\n   Index: {idx['indexname']}")
                    print(f"   Size: {idx['index_size']}")
                    print(f"   Definition: {idx['indexdef']}")

                # Check index usage
                cur.execute(
                    """
                    SELECT 
                        schemaname,
                        relname as tablename,
                        indexrelname as indexname,
                        idx_scan as index_scans,
                        idx_tup_read as tuples_read,
                        idx_tup_fetch as tuples_fetched
                    FROM pg_stat_user_indexes 
                    WHERE relname = 'langchain_pg_embedding'
                    ORDER BY idx_scan DESC
                """
                )
                index_usage = cur.fetchall()

                print("\n📈 Index Usage Statistics:")
                for usage in index_usage:
                    print(f"\n   Index: {usage['indexname']}")
                    print(f"   Scans: {usage['index_scans']:,}")
                    print(f"   Tuples read: {usage['tuples_read']:,}")
                    print(f"   Tuples fetched: {usage['tuples_fetched']:,}")

    def explain_ivfflat_tuning(self):
        """Explain IVFFlat index tuning."""
        print("\n" + "=" * 80)
        print("IVFFlat INDEX TUNING")
        print("=" * 80)

        print(
            """
IVFFlat is an approximate nearest neighbor index that:
1. Divides vectors into clusters (lists)
2. Searches only nearby clusters during query
3. Trade-off: speed vs accuracy

KEY PARAMETER: lists
- Number of clusters to create
- Rule of thumb: sqrt(total_rows) to 4*sqrt(total_rows)
- More lists = faster queries, less accurate
- Fewer lists = slower queries, more accurate

For 4,640 embeddings:
- Optimal range: 68 to 272 lists
- Current (if using 100): Good starting point
- Recommended: Test 150-200 for best balance

CREATION SYNTAX:
CREATE INDEX ON langchain_pg_embedding 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 150);

SEARCH PARAMETER: probes
- Number of clusters to search during query
- Default: 1 (fastest, least accurate)
- Recommended: 10-20 (good balance)
- Set per session:
  SET ivfflat.probes = 10;

Example performance impact:
- probes=1:  ~300ms, 80% recall
- probes=10: ~500ms, 95% recall
- probes=20: ~700ms, 98% recall
        """
        )

    def explain_hnsw_tuning(self):
        """Explain HNSW index tuning."""
        print("\n" + "=" * 80)
        print("HNSW INDEX TUNING")
        print("=" * 80)

        print(
            """
HNSW (Hierarchical Navigable Small World):
- Graph-based index (multiple layers)
- Better accuracy than IVFFlat
- Faster queries, slower build time
- Industry standard for production

KEY PARAMETERS:

1. m (connections per node)
   - Default: 16
   - Range: 4-64
   - Higher = more accurate, larger index, slower build
   - Recommended: 16 (balanced) or 32 (high accuracy)

2. ef_construction (build-time search depth)
   - Default: 64
   - Range: 32-512
   - Higher = better quality index, slower build
   - Recommended: 64 (fast build) or 128 (quality)

CREATION SYNTAX:
CREATE INDEX ON langchain_pg_embedding 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

SEARCH PARAMETER: ef_search
- Runtime search depth
- Default: 40
- Higher = more accurate, slower
- Set per session:
  SET hnsw.ef_search = 40;

Example configurations:
Fast:     m=8,  ef_construction=32,  ef_search=20  (~200ms, 90% recall)
Balanced: m=16, ef_construction=64,  ef_search=40  (~300ms, 95% recall)
Quality:  m=32, ef_construction=128, ef_search=80  (~500ms, 99% recall)

WHEN TO USE HNSW:
✅ Production systems (better QPS)
✅ When accuracy is critical
✅ When you can afford longer build time
✅ Dataset > 10k vectors

WHEN TO USE IVFFlat:
✅ Development/testing
✅ Very large datasets (>1M vectors)
✅ When fast index build needed
✅ When slight accuracy loss acceptable
        """
        )

    def benchmark_index_configs(self):
        """Benchmark different index configurations."""
        print("\n" + "=" * 80)
        print("INDEX CONFIGURATION BENCHMARK")
        print("=" * 80)

        test_query = """
        SELECT 
            cmetadata->>'chunk_id' as chunk_id,
            embedding <=> %s::vector as distance
        FROM langchain_pg_embedding
        ORDER BY embedding <=> %s::vector
        LIMIT 5
        """

        # Sample embedding (3072 dimensions of zeros for demo)
        sample_embedding = [0.0] * 3072

        configs = [
            ("Default (no tuning)", {}),
            ("IVFFlat probes=1", {"ivfflat.probes": "1"}),
            ("IVFFlat probes=10", {"ivfflat.probes": "10"}),
            ("IVFFlat probes=20", {"ivfflat.probes": "20"}),
        ]

        print("\n🔍 Testing different configurations...")
        print("   (Using sample query with zero vector)")

        with psycopg.connect(self.database_url) as conn:
            for config_name, params in configs:
                # Set parameters
                with conn.cursor() as cur:
                    for key, value in params.items():
                        cur.execute(f"SET {key} = {value}")

                    # Warm up
                    cur.execute(test_query, (sample_embedding, sample_embedding))
                    _ = cur.fetchall()

                    # Benchmark
                    times = []
                    for _ in range(5):
                        start = time.perf_counter()
                        cur.execute(test_query, (sample_embedding, sample_embedding))
                        results = cur.fetchall()
                        elapsed = (time.perf_counter() - start) * 1000
                        times.append(elapsed)

                    avg_time = sum(times) / len(times)
                    print(f"\n   {config_name}:")
                    print(f"      Avg latency: {avg_time:.2f}ms")
                    print(f"      Results: {len(results)}")


class ConnectionPoolingGuide:
    """
    Guide for PostgreSQL connection pooling.

    Without pooling:
    - Each query creates new connection (~50-200ms overhead)
    - Connection limit can be exhausted
    - Poor performance under load

    With pooling:
    - Reuse existing connections (~1-5ms overhead)
    - Control max connections
    - Better resource utilization
    - Handle concurrent requests efficiently
    """

    @staticmethod
    def explain_connection_pooling():
        """Explain connection pooling concepts."""
        print("=" * 80)
        print("CONNECTION POOLING")
        print("=" * 80)

        print(
            """
WHY CONNECTION POOLING?

Without pooling (current):
┌─────────┐     ┌──────────┐     ┌──────────┐
│ Query 1 │────▶│ Connect  │────▶│ Execute  │────▶ Close
└─────────┘     │ (~100ms) │     │ (~500ms) │
                └──────────┘     └──────────┘

┌─────────┐     ┌──────────┐     ┌──────────┐
│ Query 2 │────▶│ Connect  │────▶│ Execute  │────▶ Close
└─────────┘     │ (~100ms) │     │ (~500ms) │
                └──────────┘     └──────────┘

Total: 1200ms for 2 queries
Overhead: 200ms (connection time)

With pooling:
┌─────────────────────────────────────┐
│         Connection Pool             │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐       │
│  │ C1 │ │ C2 │ │ C3 │ │ C4 │ ...   │
│  └────┘ └────┘ └────┘ └────┘       │
└─────────────────────────────────────┘
      ▲                        ▲
      │ Borrow     Return      │
┌─────────┐                ┌─────────┐
│ Query 1 │───Execute────▶ │ Query 2 │
└─────────┘  (~500ms)      └─────────┘

Total: 1000ms for 2 queries
Overhead: 0ms (reuse connections)
Improvement: 16-20% faster

KEY PARAMETERS:

1. pool_size (core connections)
   - Always kept alive
   - Default: 5
   - Recommended: 10 for production
   - Formula: (CPU cores * 2) + disk_spindles

2. max_overflow (extra connections)
   - Created when pool exhausted
   - Closed after use
   - Default: 10
   - Recommended: 20

3. pool_timeout (wait time)
   - How long to wait for connection
   - Default: 30 seconds
   - Recommended: 10-30s

4. pool_recycle (connection lifetime)
   - Reconnect after N seconds
   - Prevents stale connections
   - Default: -1 (never)
   - Recommended: 3600 (1 hour)

5. pool_pre_ping (connection health check)
   - Test connection before use
   - Default: False
   - Recommended: True (small overhead, prevents errors)

IMPLEMENTATION OPTIONS:

1. SQLAlchemy Engine Pool (Recommended):
   from sqlalchemy import create_engine
   from sqlalchemy.pool import QueuePool
   
   engine = create_engine(
       database_url,
       poolclass=QueuePool,
       pool_size=10,           # Core connections
       max_overflow=20,        # Extra connections
       pool_timeout=30,        # Wait timeout
       pool_recycle=3600,      # Reconnect after 1h
       pool_pre_ping=True      # Health check
   )

2. psycopg3 Connection Pool:
   from psycopg_pool import ConnectionPool
   
   pool = ConnectionPool(
       database_url,
       min_size=5,             # Min connections
       max_size=20,            # Max connections
       timeout=30,             # Wait timeout
       max_idle=300            # Close idle after 5min
   )

3. PgBouncer (External, Advanced):
   - Separate pooling server
   - Connection pooling for multiple apps
   - Transaction-level pooling
   - Best for: High concurrency (100+ connections)

PERFORMANCE COMPARISON:

Scenario: 100 concurrent queries

Without pooling:
- Connection overhead: 100 * 100ms = 10,000ms
- Total time: ~60 seconds
- Database connections: 100 new connections

With pooling (pool_size=10, max_overflow=20):
- Connection overhead: ~0ms (reuse)
- Total time: ~50 seconds
- Database connections: Max 30 reused connections
- Improvement: 16-20% faster + better resource usage

MONITORING:

Check pool statistics:
engine.pool.size()       # Current pool size
engine.pool.checked_in() # Available connections
engine.pool.checked_out() # In-use connections
engine.pool.overflow()   # Extra connections
        """
        )

    @staticmethod
    def show_implementation_examples():
        """Show code examples."""
        print("\n" + "=" * 80)
        print("IMPLEMENTATION EXAMPLES")
        print("=" * 80)

        print(
            """
EXAMPLE 1: SQLAlchemy with LangChain
────────────────────────────────────────────────────────────────

from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
from langchain_postgres import PGVector
from langchain_openai import OpenAIEmbeddings

# Create engine with connection pool
engine = create_engine(
    "postgresql+psycopg://user:pass@localhost:5432/db",
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo_pool=True  # Debug logging
)

# Use with PGVector
embeddings = OpenAIEmbeddings()
vector_store = PGVector(
    embeddings=embeddings,
    collection_name="docs",
    connection=engine,  # Pass engine, not URL
    use_jsonb=True
)

# Queries now reuse connections automatically
docs = vector_store.similarity_search("query", k=5)


EXAMPLE 2: Raw psycopg3 Pool
────────────────────────────────────────────────────────────────

from psycopg_pool import ConnectionPool
import time

# Create pool
pool = ConnectionPool(
    "postgresql://user:pass@localhost:5432/db",
    min_size=5,
    max_size=20,
    timeout=30
)

# Use pool
def query_with_pool(pool, query):
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchall()

# Benchmark
start = time.time()
for i in range(100):
    results = query_with_pool(pool, "SELECT 1")
elapsed = time.time() - start

print(f"100 queries: {elapsed:.2f}s")
pool.close()


EXAMPLE 3: Compare Performance
────────────────────────────────────────────────────────────────

import time
import psycopg
from psycopg_pool import ConnectionPool

# Without pool
def benchmark_no_pool(database_url, n=50):
    times = []
    for _ in range(n):
        start = time.perf_counter()
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                _ = cur.fetchone()
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
    return sum(times) / len(times)

# With pool
def benchmark_with_pool(database_url, n=50):
    pool = ConnectionPool(database_url, min_size=5, max_size=20)
    times = []
    for _ in range(n):
        start = time.perf_counter()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                _ = cur.fetchone()
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
    pool.close()
    return sum(times) / len(times)

# Compare
database_url = "postgresql://user:pass@localhost:5432/db"
no_pool_avg = benchmark_no_pool(database_url)
with_pool_avg = benchmark_with_pool(database_url)

print(f"Without pool: {no_pool_avg:.2f}ms per query")
print(f"With pool:    {with_pool_avg:.2f}ms per query")
print(f"Improvement:  {((no_pool_avg - with_pool_avg) / no_pool_avg * 100):.1f}%")


EXAMPLE 4: Monitor Pool Health
────────────────────────────────────────────────────────────────

from sqlalchemy import create_engine

engine = create_engine(
    database_url,
    pool_size=10,
    max_overflow=20,
    echo_pool=True  # Enable logging
)

# Get pool statistics
def print_pool_stats(engine):
    pool = engine.pool
    print(f"Pool size: {pool.size()}")
    print(f"Checked in: {pool.checked_in_connections}")
    print(f"Checked out: {pool.checked_out_connections}")
    print(f"Overflow: {pool.overflow()}")
    print(f"Total: {pool.size() + pool.overflow()}")

# After running queries
print_pool_stats(engine)

# Expected output:
# Pool size: 10
# Checked in: 8
# Checked out: 2
# Overflow: 0
# Total: 10
        """
        )


def main():
    """Run demonstrations."""
    print("\n" + "=" * 80)
    print("POSTGRESQL OPTIMIZATION GUIDE")
    print("Index Tuning + Connection Pooling")
    print("=" * 80)

    # Index tuning
    tuning = IndexTuningGuide(settings.database_url)
    tuning.analyze_current_indexes()
    tuning.explain_ivfflat_tuning()
    tuning.explain_hnsw_tuning()

    # Connection pooling
    pooling = ConnectionPoolingGuide()
    pooling.explain_connection_pooling()
    pooling.show_implementation_examples()

    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print(
        """
IMMEDIATE ACTIONS:

1. Index Tuning (5 minutes):
   - Test IVFFlat with probes=10 (currently probes=1)
   - Expected: 678ms → 500-550ms
   
   SQL command:
   SET ivfflat.probes = 10;

2. Connection Pooling (15 minutes):
   - Update PGVector initialization to use SQLAlchemy engine
   - Expected: 10-15% improvement
   
3. Consider HNSW Index (1 hour):
   - Better for production
   - Expected: 678ms → 300-400ms
   - Trade-off: Longer index build time

ESTIMATED TOTAL IMPROVEMENT:
Current:     678ms average
After both:  400-450ms average (~35% faster)
With cache:  <50ms for cached queries
    """
    )

    print("\n" + "=" * 80)
    print("✅ GUIDE COMPLETE!")
    print("=" * 80)


if __name__ == "__main__":
    main()
