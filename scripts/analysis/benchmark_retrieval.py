#!/usr/bin/env python3
"""
Performance Benchmarking for RAG System
Tests retrieval performance across diverse queries with various k values and filters.
"""
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import time
import statistics
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_core.documents import Document

from src.config.models import settings


# Test queries organized by category
BENCHMARK_QUERIES = {
    "law": [
        "Điều kiện tham gia đấu thầu của nhà thầu là gì?",
        "Nhà thầu cần có những năng lực gì để tham gia đấu thầu?",
        "Quy định về hồ sơ đề xuất của nhà thầu?",
        "Thời hạn có hiệu lực của hồ sơ dự thầu?",
        "Bảo đảm dự thầu được quy định như thế nào?",
        "Các hình thức lựa chọn nhà thầu theo luật đấu thầu?",
        "Trường hợp nào phải đấu thầu rộng rãi?",
    ],
    "decree": [
        "Hồ sơ mời thầu gồm những nội dung gì?",
        "Tiêu chuẩn đánh giá hồ sơ dự thầu?",
        "Quy trình mở thầu được thực hiện như thế nào?",
        "Nội dung đánh giá về kỹ thuật trong hồ sơ dự thầu?",
        "Thành phần tổ chức chấm thầu gồm những ai?",
        "Trình tự đánh giá hồ sơ dự thầu theo nghị định?",
        "Quy định về thời gian công bố kết quả đấu thầu?",
    ],
    "bidding": [
        "Mẫu hợp đồng xây dựng có những phần nào?",
        "Biểu mẫu dự thầu cần điền những thông tin gì?",
        "Bảng dự toán chi phí xây dựng gồm các hạng mục nào?",
        "Cam kết của nhà thầu trong hồ sơ dự thầu?",
        "Mẫu bảo lãnh thực hiện hợp đồng?",
        "Điều khoản thanh toán trong hợp đồng xây dựng?",
        "Yêu cầu về tiến độ thi công trong hợp đồng?",
    ],
    "mixed": [
        "Quy trình từ đấu thầu đến ký hợp đồng?",
        "Trách nhiệm của bên mời thầu và nhà thầu?",
        "Điều kiện thanh toán và bảo lãnh trong đấu thầu?",
        "So sánh đấu thầu rộng rãi và đấu thầu hạn chế?",
        "Quy trình đánh giá và phê duyệt kết quả đấu thầu?",
    ],
}


class RetrievalBenchmark:
    """Benchmark retrieval performance."""

    def __init__(self):
        """Initialize vector store."""
        self.embeddings = OpenAIEmbeddings(model=settings.embed_model)
        self.vector_store = PGVector(
            embeddings=self.embeddings,
            collection_name=settings.collection,
            connection=settings.database_url,
            use_jsonb=True,
        )
        self.results = []

    def measure_retrieval(
        self,
        query: str,
        k: int = 3,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Measure single retrieval operation.

        Args:
            query: Search query
            k: Number of results to retrieve
            filters: Optional metadata filters

        Returns:
            Dict with timing and result info
        """
        start_time = time.perf_counter()

        if filters:
            docs = self.vector_store.similarity_search(query, k=k, filter=filters)
        else:
            docs = self.vector_store.similarity_search(query, k=k)

        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000

        # Analyze results
        doc_types = defaultdict(int)
        levels = defaultdict(int)
        for doc in docs:
            doc_types[doc.metadata.get("document_type", "unknown")] += 1
            levels[doc.metadata.get("level", "unknown")] += 1

        return {
            "query": query,
            "k": k,
            "filters": filters,
            "latency_ms": latency_ms,
            "num_results": len(docs),
            "doc_types": dict(doc_types),
            "levels": dict(levels),
        }

    def run_benchmark_suite(self, k_values: List[int] = [3, 5, 10]):
        """
        Run comprehensive benchmark across all queries and k values.

        Args:
            k_values: List of k values to test
        """
        print("=" * 80)
        print("RETRIEVAL PERFORMANCE BENCHMARK")
        print("=" * 80)
        print(f"\n🔧 Configuration:")
        print(f"   - Embedding model: {settings.embed_model}")
        print(f"   - Collection: {settings.collection}")
        print(f"   - K values to test: {k_values}")

        total_queries = sum(len(queries) for queries in BENCHMARK_QUERIES.values())
        print(f"   - Total test queries: {total_queries}")

        all_results = []

        for category, queries in BENCHMARK_QUERIES.items():
            print(f"\n{'=' * 80}")
            print(f"CATEGORY: {category.upper()}")
            print(f"{'=' * 80}")

            for k in k_values:
                print(f"\n📊 Testing with k={k}")
                print("-" * 80)

                category_results = []

                for i, query in enumerate(queries, 1):
                    # Test without filters
                    result = self.measure_retrieval(query, k=k)
                    category_results.append(result)
                    all_results.append(result)

                    print(f"   {i}. Query: {query[:50]}...")
                    print(f"      Latency: {result['latency_ms']:.2f}ms")
                    print(f"      Results: {result['num_results']}")
                    print(f"      Types: {result['doc_types']}")

                # Summary for this category + k
                latencies = [r["latency_ms"] for r in category_results]
                print(f"\n   Summary (k={k}):")
                print(f"      Avg latency: {statistics.mean(latencies):.2f}ms")
                print(f"      Min latency: {min(latencies):.2f}ms")
                print(f"      Max latency: {max(latencies):.2f}ms")
                print(f"      Median latency: {statistics.median(latencies):.2f}ms")

        # Overall summary
        self._print_overall_summary(all_results)

        return all_results

    def test_filter_performance(self):
        """Test performance impact of metadata filters."""
        print("\n" + "=" * 80)
        print("FILTER PERFORMANCE TESTING")
        print("=" * 80)

        test_query = "Điều kiện tham gia đấu thầu là gì?"
        k = 5

        # Test scenarios
        scenarios = [
            ("No filter", None),
            ("Type filter: law", {"document_type": {"$eq": "law"}}),
            ("Type filter: decree", {"document_type": {"$eq": "decree"}}),
            ("Type filter: bidding", {"document_type": {"$eq": "bidding"}}),
            ("Level filter: dieu", {"level": {"$eq": "dieu"}}),
            ("Level filter: khoan", {"level": {"$eq": "khoan"}}),
            (
                "Combined: law + dieu",
                {"document_type": {"$eq": "law"}, "level": {"$eq": "dieu"}},
            ),
            (
                "Combined: decree + khoan",
                {"document_type": {"$eq": "decree"}, "level": {"$eq": "khoan"}},
            ),
        ]

        results = []
        for name, filter_dict in scenarios:
            result = self.measure_retrieval(test_query, k=k, filters=filter_dict)
            results.append((name, result))

            print(f"\n📌 {name}")
            print(f"   Latency: {result['latency_ms']:.2f}ms")
            print(f"   Results: {result['num_results']}")
            print(f"   Types: {result['doc_types']}")

        # Compare overhead
        print("\n" + "-" * 80)
        print("Filter Overhead Analysis:")
        baseline_latency = results[0][1]["latency_ms"]
        print(f"   Baseline (no filter): {baseline_latency:.2f}ms")

        for name, result in results[1:]:
            overhead = result["latency_ms"] - baseline_latency
            overhead_pct = (overhead / baseline_latency) * 100
            print(f"   {name}: +{overhead:.2f}ms ({overhead_pct:+.1f}% overhead)")

    def _print_overall_summary(self, results: List[Dict[str, Any]]):
        """Print overall benchmark summary."""
        print("\n" + "=" * 80)
        print("OVERALL BENCHMARK SUMMARY")
        print("=" * 80)

        # Group by k value
        by_k = defaultdict(list)
        for r in results:
            by_k[r["k"]].append(r["latency_ms"])

        print("\n📊 Latency Statistics by K Value:")
        for k in sorted(by_k.keys()):
            latencies = by_k[k]
            print(f"\n   K = {k}:")
            print(f"      Mean:   {statistics.mean(latencies):.2f}ms")
            print(f"      Median: {statistics.median(latencies):.2f}ms")
            print(f"      P95:    {self._percentile(latencies, 95):.2f}ms")
            print(f"      P99:    {self._percentile(latencies, 99):.2f}ms")
            print(f"      Min:    {min(latencies):.2f}ms")
            print(f"      Max:    {max(latencies):.2f}ms")

        # Performance rating
        all_latencies = [r["latency_ms"] for r in results]
        avg_latency = statistics.mean(all_latencies)
        p95_latency = self._percentile(all_latencies, 95)

        print("\n🎯 Performance Rating:")
        if avg_latency < 200 and p95_latency < 500:
            rating = "⭐⭐⭐ EXCELLENT"
        elif avg_latency < 500 and p95_latency < 1000:
            rating = "⭐⭐ GOOD"
        elif avg_latency < 1000 and p95_latency < 2000:
            rating = "⭐ ACCEPTABLE"
        else:
            rating = "⚠️  NEEDS OPTIMIZATION"

        print(f"   {rating}")
        print(f"   - Average latency: {avg_latency:.2f}ms (target: <200ms)")
        print(f"   - P95 latency: {p95_latency:.2f}ms (target: <500ms)")

    @staticmethod
    def _percentile(data: List[float], percentile: int) -> float:
        """Calculate percentile."""
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]


def main():
    """Run benchmark."""
    benchmark = RetrievalBenchmark()

    # Run main benchmark suite
    print("\n🚀 Starting benchmark suite...\n")
    benchmark.run_benchmark_suite(k_values=[3, 5, 10])

    # Test filter performance
    benchmark.test_filter_performance()

    print("\n" + "=" * 80)
    print("✅ BENCHMARK COMPLETE!")
    print("=" * 80)


if __name__ == "__main__":
    main()
