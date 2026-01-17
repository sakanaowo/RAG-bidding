# src/utils/metrics_logger.py
"""
Metrics Logger for Performance Testing
Provides structured logging and metrics storage for load tests and benchmarks.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
import threading

# Configure module logger
logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """Metrics for a single query execution."""

    query: str
    timestamp: str
    total_time_ms: float

    # Retrieval metrics
    retrieval_mode: Optional[str] = None
    retrieval_time_ms: Optional[float] = None
    retrieval_k: Optional[int] = None
    docs_retrieved: Optional[int] = None

    # Query enhancement metrics
    enhancement_strategy: Optional[str] = None
    enhanced_queries: Optional[int] = None
    enhancement_time_ms: Optional[float] = None

    # Reranking metrics
    reranker_type: Optional[str] = None
    reranker_time_ms: Optional[float] = None
    docs_before_rerank: Optional[int] = None
    docs_after_rerank: Optional[int] = None
    reranker_fallback: Optional[bool] = None

    # Generation metrics
    generation_time_ms: Optional[float] = None
    tokens_used: Optional[int] = None

    # Cache metrics
    cache_hit: Optional[bool] = None
    cache_layer: Optional[str] = None  # L1, L2, L3

    # Error tracking
    error: Optional[str] = None
    success: bool = True

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LoadTestMetrics:
    """Aggregated metrics for a load test run."""

    test_name: str
    start_time: str
    end_time: Optional[str] = None

    # Configuration
    num_users: int = 0
    num_workers: int = 0
    connection_pool_size: int = 0

    # Summary stats
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    # Timing stats
    avg_response_time_ms: float = 0.0
    min_response_time_ms: float = float("inf")
    max_response_time_ms: float = 0.0
    p50_response_time_ms: float = 0.0
    p90_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0

    # Throughput
    requests_per_second: float = 0.0

    # Resource metrics
    gpu_memory_used_gb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    memory_usage_mb: Optional[float] = None

    # Error summary
    errors: Dict[str, int] = field(default_factory=dict)

    # Individual query metrics
    query_metrics: List[QueryMetrics] = field(default_factory=list)


class MetricsLogger:
    """
    Structured metrics logger for RAG performance testing.

    Usage:
        metrics = MetricsLogger("load_test_2024")

        with metrics.track_query("What is bidding?") as tracker:
            tracker.set_retrieval(mode="balanced", k=5, time_ms=100, docs=10)
            tracker.set_reranking(type="bge", time_ms=50, docs_before=10, docs_after=5)
            tracker.set_generation(time_ms=200, tokens=500)

        metrics.save_to_file()
    """

    def __init__(
        self,
        test_name: str,
        log_dir: Optional[Path] = None,
        enable_file_logging: bool = True,
    ):
        """
        Initialize metrics logger.

        Args:
            test_name: Name of the test run
            log_dir: Directory to save logs (default: logs/metrics/)
            enable_file_logging: Whether to save logs to files
        """
        self.test_name = test_name
        self.log_dir = (
            log_dir or Path(__file__).parent.parent.parent / "logs" / "metrics"
        )
        self.enable_file_logging = enable_file_logging

        # Create log directory
        if self.enable_file_logging:
            self.log_dir.mkdir(parents=True, exist_ok=True)

        # Initialize metrics
        self.load_test = LoadTestMetrics(
            test_name=test_name,
            start_time=datetime.now().isoformat(),
        )

        # Thread-safe query collection
        self._lock = threading.Lock()
        self._response_times: List[float] = []

        logger.info(f"📊 MetricsLogger initialized: {test_name}")

    def configure_test(
        self,
        num_users: int = 0,
        num_workers: int = 0,
        connection_pool_size: int = 0,
    ):
        """Configure test parameters."""
        self.load_test.num_users = num_users
        self.load_test.num_workers = num_workers
        self.load_test.connection_pool_size = connection_pool_size

    @contextmanager
    def track_query(self, query: str):
        """
        Context manager to track a single query's performance.

        Usage:
            with metrics.track_query("query") as tracker:
                tracker.set_retrieval(...)
                # ... do work ...
        """
        start_time = time.perf_counter()
        tracker = QueryTracker(query)

        try:
            yield tracker
            tracker.success = True
        except Exception as e:
            tracker.success = False
            tracker.error = str(e)
            logger.error(f"Query failed: {e}")
            raise
        finally:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            tracker.total_time_ms = elapsed_ms

            # Create metrics object
            metrics = QueryMetrics(
                query=query,
                timestamp=datetime.now().isoformat(),
                total_time_ms=elapsed_ms,
                retrieval_mode=tracker.retrieval_mode,
                retrieval_time_ms=tracker.retrieval_time_ms,
                retrieval_k=tracker.retrieval_k,
                docs_retrieved=tracker.docs_retrieved,
                enhancement_strategy=tracker.enhancement_strategy,
                enhanced_queries=tracker.enhanced_queries,
                enhancement_time_ms=tracker.enhancement_time_ms,
                reranker_type=tracker.reranker_type,
                reranker_time_ms=tracker.reranker_time_ms,
                docs_before_rerank=tracker.docs_before_rerank,
                docs_after_rerank=tracker.docs_after_rerank,
                reranker_fallback=tracker.reranker_fallback,
                generation_time_ms=tracker.generation_time_ms,
                tokens_used=tracker.tokens_used,
                cache_hit=tracker.cache_hit,
                cache_layer=tracker.cache_layer,
                error=tracker.error,
                success=tracker.success,
                metadata=tracker.metadata,
            )

            # Thread-safe append
            with self._lock:
                self.load_test.query_metrics.append(metrics)
                self._response_times.append(elapsed_ms)
                self.load_test.total_requests += 1
                if tracker.success:
                    self.load_test.successful_requests += 1
                else:
                    self.load_test.failed_requests += 1
                    error_type = tracker.error or "Unknown"
                    self.load_test.errors[error_type] = (
                        self.load_test.errors.get(error_type, 0) + 1
                    )

    def log_query_direct(self, metrics: QueryMetrics):
        """Add query metrics directly (for async usage)."""
        with self._lock:
            self.load_test.query_metrics.append(metrics)
            self._response_times.append(metrics.total_time_ms)
            self.load_test.total_requests += 1
            if metrics.success:
                self.load_test.successful_requests += 1
            else:
                self.load_test.failed_requests += 1

    def finalize(self):
        """Finalize metrics and calculate aggregates."""
        self.load_test.end_time = datetime.now().isoformat()

        if not self._response_times:
            return

        # Calculate timing stats
        sorted_times = sorted(self._response_times)
        n = len(sorted_times)

        self.load_test.avg_response_time_ms = sum(sorted_times) / n
        self.load_test.min_response_time_ms = sorted_times[0]
        self.load_test.max_response_time_ms = sorted_times[-1]
        self.load_test.p50_response_time_ms = sorted_times[int(n * 0.5)]
        self.load_test.p90_response_time_ms = sorted_times[int(n * 0.9)]
        self.load_test.p99_response_time_ms = sorted_times[min(int(n * 0.99), n - 1)]

        # Calculate throughput
        start = datetime.fromisoformat(self.load_test.start_time)
        end = datetime.fromisoformat(self.load_test.end_time)
        duration_seconds = (end - start).total_seconds()
        if duration_seconds > 0:
            self.load_test.requests_per_second = n / duration_seconds

        logger.info(
            f"📊 Metrics finalized: {n} requests, avg={self.load_test.avg_response_time_ms:.1f}ms"
        )

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary as dictionary."""
        self.finalize()

        return {
            "test_name": self.load_test.test_name,
            "duration": {
                "start": self.load_test.start_time,
                "end": self.load_test.end_time,
            },
            "configuration": {
                "users": self.load_test.num_users,
                "workers": self.load_test.num_workers,
                "connection_pool": self.load_test.connection_pool_size,
            },
            "requests": {
                "total": self.load_test.total_requests,
                "successful": self.load_test.successful_requests,
                "failed": self.load_test.failed_requests,
                "success_rate": self.load_test.successful_requests
                / max(self.load_test.total_requests, 1),
            },
            "latency_ms": {
                "avg": round(self.load_test.avg_response_time_ms, 2),
                "min": round(self.load_test.min_response_time_ms, 2),
                "max": round(self.load_test.max_response_time_ms, 2),
                "p50": round(self.load_test.p50_response_time_ms, 2),
                "p90": round(self.load_test.p90_response_time_ms, 2),
                "p99": round(self.load_test.p99_response_time_ms, 2),
            },
            "throughput": {
                "rps": round(self.load_test.requests_per_second, 2),
            },
            "errors": self.load_test.errors,
        }

    def print_summary(self):
        """Print formatted metrics summary."""
        summary = self.get_summary()

        print("\n" + "=" * 70)
        print(f"📊 METRICS SUMMARY: {summary['test_name']}")
        print("=" * 70)

        print(f"\n⚙️  Configuration:")
        print(f"   Users: {summary['configuration']['users']}")
        print(f"   Workers: {summary['configuration']['workers']}")
        print(f"   Connection Pool: {summary['configuration']['connection_pool']}")

        print(f"\n📈 Requests:")
        print(f"   Total: {summary['requests']['total']}")
        print(f"   Successful: {summary['requests']['successful']}")
        print(f"   Failed: {summary['requests']['failed']}")
        print(f"   Success Rate: {summary['requests']['success_rate']*100:.1f}%")

        print(f"\n⏱️  Latency (ms):")
        print(f"   Average: {summary['latency_ms']['avg']:.1f}")
        print(f"   Min: {summary['latency_ms']['min']:.1f}")
        print(f"   Max: {summary['latency_ms']['max']:.1f}")
        print(f"   P50: {summary['latency_ms']['p50']:.1f}")
        print(f"   P90: {summary['latency_ms']['p90']:.1f}")
        print(f"   P99: {summary['latency_ms']['p99']:.1f}")

        print(f"\n🚀 Throughput:")
        print(f"   RPS: {summary['throughput']['rps']:.2f}")

        if summary["errors"]:
            print(f"\n❌ Errors:")
            for error, count in summary["errors"].items():
                print(f"   {error}: {count}")

        print("\n" + "=" * 70)

    def save_to_file(self, filename: Optional[str] = None) -> Path:
        """
        Save metrics to JSON file.

        Args:
            filename: Optional custom filename

        Returns:
            Path to saved file
        """
        self.finalize()

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.test_name}_{timestamp}.json"

        filepath = self.log_dir / filename

        # Convert to dict for JSON serialization
        data = {
            "summary": self.get_summary(),
            "query_metrics": [asdict(q) for q in self.load_test.query_metrics],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"📁 Metrics saved to: {filepath}")
        return filepath

    def save_summary_csv(self, filename: Optional[str] = None) -> Path:
        """Save query metrics to CSV for easy analysis."""
        import csv

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.test_name}_{timestamp}.csv"

        filepath = self.log_dir / filename

        # CSV columns
        columns = [
            "timestamp",
            "query",
            "total_time_ms",
            "retrieval_mode",
            "retrieval_time_ms",
            "retrieval_k",
            "docs_retrieved",
            "reranker_type",
            "reranker_time_ms",
            "reranker_fallback",
            "generation_time_ms",
            "cache_hit",
            "cache_layer",
            "success",
            "error",
        ]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()

            for q in self.load_test.query_metrics:
                row = {col: getattr(q, col, None) for col in columns}
                writer.writerow(row)

        logger.info(f"📁 CSV saved to: {filepath}")
        return filepath


class QueryTracker:
    """Helper class to track metrics for a single query."""

    def __init__(self, query: str):
        self.query = query
        self.total_time_ms: float = 0.0
        self.success: bool = True
        self.error: Optional[str] = None

        # Retrieval
        self.retrieval_mode: Optional[str] = None
        self.retrieval_time_ms: Optional[float] = None
        self.retrieval_k: Optional[int] = None
        self.docs_retrieved: Optional[int] = None

        # Enhancement
        self.enhancement_strategy: Optional[str] = None
        self.enhanced_queries: Optional[int] = None
        self.enhancement_time_ms: Optional[float] = None

        # Reranking
        self.reranker_type: Optional[str] = None
        self.reranker_time_ms: Optional[float] = None
        self.docs_before_rerank: Optional[int] = None
        self.docs_after_rerank: Optional[int] = None
        self.reranker_fallback: Optional[bool] = None

        # Generation
        self.generation_time_ms: Optional[float] = None
        self.tokens_used: Optional[int] = None

        # Cache
        self.cache_hit: Optional[bool] = None
        self.cache_layer: Optional[str] = None

        # Extra metadata
        self.metadata: Dict[str, Any] = {}

    def set_retrieval(
        self,
        mode: Optional[str] = None,
        time_ms: Optional[float] = None,
        k: Optional[int] = None,
        docs: Optional[int] = None,
    ):
        """Set retrieval metrics."""
        if mode:
            self.retrieval_mode = mode
        if time_ms:
            self.retrieval_time_ms = time_ms
        if k:
            self.retrieval_k = k
        if docs:
            self.docs_retrieved = docs

    def set_enhancement(
        self,
        strategy: Optional[str] = None,
        queries: Optional[int] = None,
        time_ms: Optional[float] = None,
    ):
        """Set query enhancement metrics."""
        if strategy:
            self.enhancement_strategy = strategy
        if queries:
            self.enhanced_queries = queries
        if time_ms:
            self.enhancement_time_ms = time_ms

    def set_reranking(
        self,
        type: Optional[str] = None,
        time_ms: Optional[float] = None,
        docs_before: Optional[int] = None,
        docs_after: Optional[int] = None,
        fallback: Optional[bool] = None,
    ):
        """Set reranking metrics."""
        if type:
            self.reranker_type = type
        if time_ms:
            self.reranker_time_ms = time_ms
        if docs_before:
            self.docs_before_rerank = docs_before
        if docs_after:
            self.docs_after_rerank = docs_after
        if fallback is not None:
            self.reranker_fallback = fallback

    def set_generation(
        self,
        time_ms: Optional[float] = None,
        tokens: Optional[int] = None,
    ):
        """Set generation metrics."""
        if time_ms:
            self.generation_time_ms = time_ms
        if tokens:
            self.tokens_used = tokens

    def set_cache(
        self,
        hit: Optional[bool] = None,
        layer: Optional[str] = None,
    ):
        """Set cache metrics."""
        if hit is not None:
            self.cache_hit = hit
        if layer:
            self.cache_layer = layer


# ============================================================================
# Convenience functions for quick logging
# ============================================================================

_default_logger: Optional[MetricsLogger] = None


def get_metrics_logger(test_name: str = "default") -> MetricsLogger:
    """Get or create a default metrics logger."""
    global _default_logger
    if _default_logger is None or _default_logger.test_name != test_name:
        _default_logger = MetricsLogger(test_name)
    return _default_logger


def log_request_metrics(
    query: str,
    total_time_ms: float,
    success: bool = True,
    error: Optional[str] = None,
    **kwargs,
):
    """
    Quick function to log a single request's metrics.

    Args:
        query: The query string
        total_time_ms: Total response time in milliseconds
        success: Whether the request succeeded
        error: Error message if failed
        **kwargs: Additional metrics (retrieval_mode, reranker_type, etc.)
    """
    metrics = QueryMetrics(
        query=query,
        timestamp=datetime.now().isoformat(),
        total_time_ms=total_time_ms,
        success=success,
        error=error,
        **{k: v for k, v in kwargs.items() if k in QueryMetrics.__dataclass_fields__},
    )

    logger = get_metrics_logger()
    logger.log_query_direct(metrics)


# ============================================================================
# Example usage and testing
# ============================================================================

if __name__ == "__main__":
    import random

    print("=" * 70)
    print("METRICS LOGGER TEST")
    print("=" * 70)

    # Create logger
    metrics = MetricsLogger("test_load_run")
    metrics.configure_test(num_users=100, num_workers=4, connection_pool_size=50)

    # Simulate some queries
    test_queries = [
        "Điều kiện tham gia đấu thầu là gì?",
        "Quy trình đánh giá hồ sơ dự thầu?",
        "Hồ sơ mời thầu bao gồm những gì?",
        "Thời gian chuẩn bị hồ sơ dự thầu?",
        "Cách tính giá dự thầu?",
    ]

    for _ in range(20):
        query = random.choice(test_queries)

        with metrics.track_query(query) as tracker:
            # Simulate retrieval
            time.sleep(random.uniform(0.05, 0.15))
            tracker.set_retrieval(
                mode="balanced",
                time_ms=random.uniform(50, 150),
                k=5,
                docs=random.randint(3, 10),
            )

            # Simulate reranking
            time.sleep(random.uniform(0.02, 0.08))
            tracker.set_reranking(
                type="bge" if random.random() > 0.2 else "openai",
                time_ms=random.uniform(20, 80),
                docs_before=random.randint(8, 15),
                docs_after=5,
                fallback=random.random() > 0.9,
            )

            # Simulate generation
            time.sleep(random.uniform(0.1, 0.3))
            tracker.set_generation(
                time_ms=random.uniform(100, 300), tokens=random.randint(200, 800)
            )

            # Simulate cache
            tracker.set_cache(
                hit=random.random() > 0.6, layer=random.choice(["L1", "L2", "L3"])
            )

    # Print and save results
    metrics.print_summary()

    json_path = metrics.save_to_file()
    csv_path = metrics.save_summary_csv()

    print(f"\n✅ JSON saved to: {json_path}")
    print(f"✅ CSV saved to: {csv_path}")
