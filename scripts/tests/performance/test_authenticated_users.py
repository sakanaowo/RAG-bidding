#!/usr/bin/env python3
"""
Multi-User Performance Test with Authenticated Users
Test hiệu năng với 100 users đã được đăng ký, gửi các requests khác nhau
"""

import asyncio
import aiohttp
import time
import random
import statistics
import json
import sys
import os
import logging
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import argparse
from threading import Lock
from tqdm import tqdm

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Thêm src vào Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from scripts.tests.performance.create_test_users import get_user_credentials


# =============================================================================
# CONFIGURATION
# =============================================================================

API_BASE_URL = "http://localhost:8000"
API_PREFIX = "/api"  # API routes prefix

# Các loại request khác nhau để test
REQUEST_TYPES = {
    "conversation_create": {"weight": 0.15, "description": "Tạo conversation mới"},
    "conversation_list": {"weight": 0.20, "description": "Liệt kê conversations"},
    "message_send": {"weight": 0.35, "description": "Gửi tin nhắn (RAG query)"},
    "conversation_get": {"weight": 0.15, "description": "Lấy chi tiết conversation"},
    "user_profile": {"weight": 0.10, "description": "Lấy thông tin user"},
    "logout": {"weight": 0.05, "description": "Logout"},
}

# Các câu hỏi để test RAG
RAG_QUERIES = [
    # Câu hỏi về quy trình đấu thầu
    "Quy trình đấu thầu rộng rãi gồm những bước nào?",
    "Các hình thức lựa chọn nhà thầu theo Luật đấu thầu 2023?",
    "Điều kiện để được chỉ định thầu?",
    "Thời hạn nộp hồ sơ dự thầu là bao lâu?",
    # Câu hỏi về hồ sơ
    "Hồ sơ mời thầu cần có những nội dung gì?",
    "Hồ sơ dự thầu gồm những tài liệu nào?",
    "Bảo đảm dự thầu được quy định như thế nào?",
    "Yêu cầu về năng lực kinh nghiệm của nhà thầu?",
    # Câu hỏi về đánh giá
    "Tiêu chí đánh giá hồ sơ dự thầu?",
    "Quy trình thẩm định kết quả lựa chọn nhà thầu?",
    "Phương pháp chấm điểm hồ sơ dự thầu?",
    "Cách xử lý khi có hai nhà thầu điểm bằng nhau?",
    # Câu hỏi về xử lý vi phạm
    "Xử lý vi phạm trong đấu thầu như thế nào?",
    "Trường hợp nào hủy thầu?",
    "Quy trình khiếu nại trong đấu thầu?",
    "Chế tài với nhà thầu vi phạm?",
    # Câu hỏi ngắn
    "chỉ định thầu",
    "đấu thầu qua mạng",
    "bảo đảm thực hiện hợp đồng",
    "ký kết hợp đồng",
]

# Chỉ dùng fast mode để tránh bottleneck OpenAI
RAG_MODES = ["fast", "balanced", "quality", "adaptive"]


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class RequestResult:
    """Kết quả của một request"""

    user_id: int
    request_type: str
    success: bool
    status_code: int
    response_time_ms: float
    error: Optional[str] = None
    extra_data: Dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class UserSession:
    """Session của một user"""

    user_id: int
    email: str
    access_token: Optional[str] = None
    conversation_id: Optional[str] = None
    results: List[RequestResult] = field(default_factory=list)


@dataclass
class TestSummary:
    """Tổng kết kết quả test"""

    total_users: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    total_time_seconds: float
    requests_per_second: float
    avg_response_time_ms: float
    median_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    by_request_type: Dict[str, Dict] = field(default_factory=dict)
    errors: List[Dict] = field(default_factory=list)


# =============================================================================
# PERFORMANCE TESTER CLASS
# =============================================================================


class AuthenticatedPerformanceTester:
    """Performance tester với authenticated users"""

    def __init__(
        self, base_url: str = API_BASE_URL, num_users: int = 100, verbose: bool = False
    ):
        self.base_url = base_url
        self.num_users = num_users
        self.user_sessions: Dict[int, UserSession] = {}
        self.all_results: List[RequestResult] = []
        self.verbose = verbose

        # Progress tracking
        self._lock = Lock()
        self._requests_completed = 0
        self._requests_success = 0
        self._requests_failed = 0
        self._current_batch_start_time = None

        # Real-time stats by type
        self._live_stats = defaultdict(
            lambda: {"count": 0, "success": 0, "total_time": 0}
        )

        # Progress bar for current batch
        self._current_pbar = None

    def _log_request(self, result: RequestResult):
        """Log và cập nhật stats cho một request"""
        with self._lock:
            self._requests_completed += 1
            if result.success:
                self._requests_success += 1
            else:
                self._requests_failed += 1

            # Update live stats
            self._live_stats[result.request_type]["count"] += 1
            if result.success:
                self._live_stats[result.request_type]["success"] += 1
                self._live_stats[result.request_type][
                    "total_time"
                ] += result.response_time_ms

            # Update progress bar
            if self._current_pbar is not None:
                status = "✓" if result.success else "✗"
                self._current_pbar.set_postfix_str(
                    f"{status} {result.request_type} | {result.response_time_ms:.0f}ms"
                )
                self._current_pbar.update(1)

            # Log if verbose
            if self.verbose:
                status = "✓" if result.success else "✗"
                time_str = (
                    f"{result.response_time_ms:.0f}ms"
                    if result.response_time_ms > 0
                    else "-"
                )
                error_str = f" | {result.error[:50]}" if result.error else ""
                logger.info(
                    f"[User {result.user_id:03d}] {status} {result.request_type:<20} | "
                    f"{time_str:>8}{error_str}"
                )

    def _print_live_stats(self):
        """In thống kê realtime"""
        with self._lock:
            total = self._requests_completed
            success = self._requests_success
            failed = self._requests_failed
            rate = (success / total * 100) if total > 0 else 0

            print(
                f"\r   📊 Progress: {total} requests | ✅ {success} | ❌ {failed} | Rate: {rate:.1f}%",
                end="",
                flush=True,
            )

    def _print_batch_stats(self):
        """In thống kê cho batch hiện tại"""
        with self._lock:
            print(f"   📈 Request stats by type:")
            for req_type, stats in sorted(self._live_stats.items()):
                if stats["count"] > 0:
                    success_rate = stats["success"] / stats["count"] * 100
                    avg_time = (
                        stats["total_time"] / stats["success"]
                        if stats["success"] > 0
                        else 0
                    )
                    print(
                        f"      • {req_type:<22}: {stats['success']:>4}/{stats['count']:<4} ({success_rate:>5.1f}%) | avg: {avg_time:>8.0f}ms"
                    )

    async def check_health(self) -> bool:
        """Kiểm tra server health"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health", timeout=5) as resp:
                    return resp.status == 200
        except Exception as e:
            print(f"❌ Server health check failed: {e}")
            return False

    async def login_user(
        self, session: aiohttp.ClientSession, email: str, password: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Login user và lấy access token

        Returns:
            Tuple of (access_token, error)
        """
        try:
            async with session.post(
                f"{self.base_url}{API_PREFIX}/auth/login",
                json={"email": email, "password": password},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    tokens = data.get("tokens", {})
                    return tokens.get("access_token"), None
                else:
                    error_text = await resp.text()
                    return None, f"HTTP {resp.status}: {error_text}"
        except Exception as e:
            return None, str(e)

    async def make_request(
        self,
        session: aiohttp.ClientSession,
        user_session: UserSession,
        request_type: str,
    ) -> RequestResult:
        """Thực hiện một request dựa trên loại"""

        headers = {"Authorization": f"Bearer {user_session.access_token}"}
        start_time = time.time()

        try:
            if request_type == "conversation_create":
                return await self._create_conversation(
                    session, user_session, headers, start_time
                )

            elif request_type == "conversation_list":
                return await self._list_conversations(
                    session, user_session, headers, start_time
                )

            elif request_type == "message_send":
                return await self._send_message(
                    session, user_session, headers, start_time
                )

            elif request_type == "conversation_get":
                return await self._get_conversation(
                    session, user_session, headers, start_time
                )

            elif request_type == "user_profile":
                return await self._get_profile(
                    session, user_session, headers, start_time
                )

            elif request_type == "logout":
                return await self._logout(session, user_session, headers, start_time)

            else:
                return RequestResult(
                    user_id=user_session.user_id,
                    request_type=request_type,
                    success=False,
                    status_code=0,
                    response_time_ms=(time.time() - start_time) * 1000,
                    error=f"Unknown request type: {request_type}",
                )

        except asyncio.TimeoutError:
            return RequestResult(
                user_id=user_session.user_id,
                request_type=request_type,
                success=False,
                status_code=0,
                response_time_ms=(time.time() - start_time) * 1000,
                error="Request timeout",
            )
        except Exception as e:
            return RequestResult(
                user_id=user_session.user_id,
                request_type=request_type,
                success=False,
                status_code=0,
                response_time_ms=(time.time() - start_time) * 1000,
                error=str(e),
            )

    async def _create_conversation(
        self,
        session: aiohttp.ClientSession,
        user_session: UserSession,
        headers: Dict,
        start_time: float,
    ) -> RequestResult:
        """Tạo conversation mới"""
        rag_mode = random.choice(RAG_MODES)

        async with session.post(
            f"{self.base_url}{API_PREFIX}/conversations",
            json={
                "title": f"Test conversation {user_session.user_id}",
                "rag_mode": rag_mode,
            },
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            response_time = (time.time() - start_time) * 1000

            if resp.status == 201:
                data = await resp.json()
                user_session.conversation_id = data.get("id")
                return RequestResult(
                    user_id=user_session.user_id,
                    request_type="conversation_create",
                    success=True,
                    status_code=resp.status,
                    response_time_ms=response_time,
                    extra_data={"conversation_id": user_session.conversation_id},
                )
            else:
                error_text = await resp.text()
                return RequestResult(
                    user_id=user_session.user_id,
                    request_type="conversation_create",
                    success=False,
                    status_code=resp.status,
                    response_time_ms=response_time,
                    error=error_text[:200],
                )

    async def _list_conversations(
        self,
        session: aiohttp.ClientSession,
        user_session: UserSession,
        headers: Dict,
        start_time: float,
    ) -> RequestResult:
        """Liệt kê conversations của user"""
        async with session.get(
            f"{self.base_url}{API_PREFIX}/conversations",
            params={"skip": 0, "limit": 20},
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            response_time = (time.time() - start_time) * 1000

            if resp.status == 200:
                data = await resp.json()
                # Lấy conversation_id đầu tiên nếu chưa có
                if not user_session.conversation_id:
                    conversations = data.get("conversations", [])
                    if conversations:
                        user_session.conversation_id = conversations[0].get("id")

                return RequestResult(
                    user_id=user_session.user_id,
                    request_type="conversation_list",
                    success=True,
                    status_code=resp.status,
                    response_time_ms=response_time,
                    extra_data={"count": data.get("total", 0)},
                )
            else:
                return RequestResult(
                    user_id=user_session.user_id,
                    request_type="conversation_list",
                    success=False,
                    status_code=resp.status,
                    response_time_ms=response_time,
                    error=await resp.text(),
                )

    async def _send_message(
        self,
        session: aiohttp.ClientSession,
        user_session: UserSession,
        headers: Dict,
        start_time: float,
    ) -> RequestResult:
        """Gửi tin nhắn RAG"""
        # Tạo conversation nếu chưa có
        if not user_session.conversation_id:
            create_result = await self._create_conversation(
                session, user_session, headers, time.time()
            )
            if not create_result.success:
                return RequestResult(
                    user_id=user_session.user_id,
                    request_type="message_send",
                    success=False,
                    status_code=0,
                    response_time_ms=(time.time() - start_time) * 1000,
                    error="Failed to create conversation for message",
                )

        query = random.choice(RAG_QUERIES)

        async with session.post(
            f"{self.base_url}{API_PREFIX}/conversations/{user_session.conversation_id}/messages",
            json={"content": query},
            headers=headers,
            timeout=aiohttp.ClientTimeout(
                total=120
            ),  # RAG queries có thể mất thời gian
        ) as resp:
            response_time = (time.time() - start_time) * 1000

            if resp.status in [200, 201]:
                data = await resp.json()
                return RequestResult(
                    user_id=user_session.user_id,
                    request_type="message_send",
                    success=True,
                    status_code=resp.status,
                    response_time_ms=response_time,
                    extra_data={
                        "query_length": len(query),
                        "answer_length": len(
                            data.get("assistant_message", {}).get("content", "")
                        ),
                        "processing_time_ms": data.get("assistant_message", {}).get(
                            "processing_time_ms", 0
                        ),
                    },
                )
            else:
                return RequestResult(
                    user_id=user_session.user_id,
                    request_type="message_send",
                    success=False,
                    status_code=resp.status,
                    response_time_ms=response_time,
                    error=await resp.text(),
                )

    async def _get_conversation(
        self,
        session: aiohttp.ClientSession,
        user_session: UserSession,
        headers: Dict,
        start_time: float,
    ) -> RequestResult:
        """Lấy chi tiết conversation"""
        if not user_session.conversation_id:
            # Thử list conversations trước
            list_result = await self._list_conversations(
                session, user_session, headers, time.time()
            )
            if not user_session.conversation_id:
                return RequestResult(
                    user_id=user_session.user_id,
                    request_type="conversation_get",
                    success=False,
                    status_code=0,
                    response_time_ms=(time.time() - start_time) * 1000,
                    error="No conversation available",
                )

        async with session.get(
            f"{self.base_url}{API_PREFIX}/conversations/{user_session.conversation_id}",
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            response_time = (time.time() - start_time) * 1000

            if resp.status == 200:
                data = await resp.json()
                return RequestResult(
                    user_id=user_session.user_id,
                    request_type="conversation_get",
                    success=True,
                    status_code=resp.status,
                    response_time_ms=response_time,
                    extra_data={"message_count": data.get("message_count", 0)},
                )
            else:
                return RequestResult(
                    user_id=user_session.user_id,
                    request_type="conversation_get",
                    success=False,
                    status_code=resp.status,
                    response_time_ms=response_time,
                    error=await resp.text(),
                )

    async def _get_profile(
        self,
        session: aiohttp.ClientSession,
        user_session: UserSession,
        headers: Dict,
        start_time: float,
    ) -> RequestResult:
        """Lấy profile user"""
        async with session.get(
            f"{self.base_url}{API_PREFIX}/auth/me",
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            response_time = (time.time() - start_time) * 1000

            return RequestResult(
                user_id=user_session.user_id,
                request_type="user_profile",
                success=resp.status == 200,
                status_code=resp.status,
                response_time_ms=response_time,
                error=await resp.text() if resp.status != 200 else None,
            )

    async def _logout(
        self,
        session: aiohttp.ClientSession,
        user_session: UserSession,
        headers: Dict,
        start_time: float,
    ) -> RequestResult:
        """Logout user"""
        async with session.post(
            f"{self.base_url}{API_PREFIX}/auth/logout",
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            response_time = (time.time() - start_time) * 1000

            return RequestResult(
                user_id=user_session.user_id,
                request_type="logout",
                success=resp.status == 200,
                status_code=resp.status,
                response_time_ms=response_time,
                error=await resp.text() if resp.status != 200 else None,
            )

    def _select_request_type(self) -> str:
        """Chọn loại request dựa trên weight"""
        rand = random.random()
        cumulative = 0
        for request_type, config in REQUEST_TYPES.items():
            cumulative += config["weight"]
            if rand < cumulative:
                return request_type
        return "conversation_list"  # fallback

    async def user_workflow(
        self,
        session: aiohttp.ClientSession,
        user_id: int,
        credentials: Dict,
        requests_per_user: int,
        delay_range: Tuple[float, float],
    ) -> UserSession:
        """
        Workflow của một user: login -> thực hiện nhiều requests -> (optional) logout
        """
        user_session = UserSession(user_id=user_id, email=credentials["email"])

        # Login
        token, error = await self.login_user(
            session, credentials["email"], credentials["password"]
        )

        if error:
            user_session.results.append(
                RequestResult(
                    user_id=user_id,
                    request_type="login",
                    success=False,
                    status_code=0,
                    response_time_ms=0,
                    error=error,
                )
            )
            return user_session

        user_session.access_token = token
        user_session.results.append(
            RequestResult(
                user_id=user_id,
                request_type="login",
                success=True,
                status_code=200,
                response_time_ms=0,
            )
        )

        # Thực hiện các requests
        for i in range(requests_per_user):
            request_type = self._select_request_type()
            result = await self.make_request(session, user_session, request_type)
            user_session.results.append(result)

            # Log request result
            self._log_request(result)

            # Random delay giữa các requests
            if i < requests_per_user - 1:
                delay = random.uniform(delay_range[0], delay_range[1])
                await asyncio.sleep(delay)

        return user_session

    async def run_test(
        self,
        requests_per_user: int = 10,
        delay_range: Tuple[float, float] = (0.5, 2.0),
        concurrent_batch_size: int = 20,
    ) -> TestSummary:
        """
        Chạy performance test với tất cả users

        Args:
            requests_per_user: Số requests mỗi user thực hiện
            delay_range: Khoảng delay giữa các requests (min, max) seconds
            concurrent_batch_size: Số users chạy đồng thời trong một batch
        """
        print(f"\n{'='*70}")
        print(f"🚀 AUTHENTICATED MULTI-USER PERFORMANCE TEST")
        print(f"{'='*70}")
        print(f"📊 Configuration:")
        print(f"   • Users: {self.num_users}")
        print(f"   • Requests per user: {requests_per_user}")
        print(f"   • Total expected requests: {self.num_users * requests_per_user}")
        print(f"   • Delay range: {delay_range[0]:.1f}s - {delay_range[1]:.1f}s")
        print(f"   • Concurrent batch size: {concurrent_batch_size}")
        print(f"{'='*70}\n")

        # Check health
        if not await self.check_health():
            print("❌ Server is not healthy. Aborting test.")
            return None

        print("✅ Server health check passed\n")

        # Get credentials
        credentials = get_user_credentials(1, self.num_users)

        start_time = time.time()
        all_sessions: List[UserSession] = []

        # Run in batches to avoid overwhelming the server
        connector = aiohttp.TCPConnector(
            limit=concurrent_batch_size * 2
        )  # Allow more connections
        async with aiohttp.ClientSession(connector=connector) as session:
            for batch_start in range(0, self.num_users, concurrent_batch_size):
                batch_end = min(batch_start + concurrent_batch_size, self.num_users)
                batch_num = batch_start // concurrent_batch_size + 1
                total_batches = (
                    self.num_users + concurrent_batch_size - 1
                ) // concurrent_batch_size

                batch_start_time = time.time()
                self._current_batch_start_time = batch_start_time

                print(
                    f"\n📤 Batch {batch_num}/{total_batches}: users {batch_start + 1}-{batch_end}"
                )

                # Tạo progress bar cho batch này
                expected_requests = (batch_end - batch_start) * requests_per_user
                self._current_pbar = tqdm(
                    total=expected_requests,
                    desc=f"   Batch {batch_num}/{total_batches}",
                    unit="req",
                    ncols=100,
                    leave=True,
                )

                tasks = []
                for i in range(batch_start, batch_end):
                    task = self.user_workflow(
                        session, i + 1, credentials[i], requests_per_user, delay_range
                    )
                    tasks.append(task)

                batch_sessions = await asyncio.gather(*tasks, return_exceptions=True)

                # Đóng progress bar
                if self._current_pbar is not None:
                    self._current_pbar.close()
                    self._current_pbar = None

                batch_time = time.time() - batch_start_time
                successful_users = len(
                    [r for r in batch_sessions if not isinstance(r, Exception)]
                )

                for result in batch_sessions:
                    if isinstance(result, Exception):
                        print(f"   ⚠️  User error: {result}")
                    else:
                        all_sessions.append(result)
                        self.all_results.extend(result.results)

                # Print batch summary with live stats
                print(f"\n   ✅ Batch {batch_num} completed in {batch_time:.1f}s")
                print(f"   👥 Users: {successful_users}/{batch_end - batch_start}")
                self._print_batch_stats()

        total_time = time.time() - start_time

        # Generate summary
        summary = self._generate_summary(total_time)
        self._print_summary(summary)

        return summary

    def _generate_summary(self, total_time: float) -> TestSummary:
        """Generate test summary from results"""
        successful = [r for r in self.all_results if r.success]
        failed = [r for r in self.all_results if not r.success]

        response_times = [
            r.response_time_ms for r in successful if r.response_time_ms > 0
        ]

        # By request type breakdown
        by_type = defaultdict(lambda: {"success": 0, "failed": 0, "times": []})
        for r in self.all_results:
            if r.success:
                by_type[r.request_type]["success"] += 1
                by_type[r.request_type]["times"].append(r.response_time_ms)
            else:
                by_type[r.request_type]["failed"] += 1

        by_type_summary = {}
        for req_type, data in by_type.items():
            times = data["times"]
            by_type_summary[req_type] = {
                "success": data["success"],
                "failed": data["failed"],
                "total": data["success"] + data["failed"],
                "success_rate": (
                    data["success"] / (data["success"] + data["failed"])
                    if (data["success"] + data["failed"]) > 0
                    else 0
                ),
                "avg_time_ms": statistics.mean(times) if times else 0,
                "median_time_ms": statistics.median(times) if times else 0,
                "min_time_ms": min(times) if times else 0,
                "max_time_ms": max(times) if times else 0,
            }

        # Collect errors
        errors = []
        for r in failed[:20]:  # Top 20 errors
            errors.append(
                {
                    "user_id": r.user_id,
                    "request_type": r.request_type,
                    "error": r.error[:100] if r.error else "Unknown",
                    "status_code": r.status_code,
                }
            )

        return TestSummary(
            total_users=self.num_users,
            total_requests=len(self.all_results),
            successful_requests=len(successful),
            failed_requests=len(failed),
            success_rate=(
                len(successful) / len(self.all_results) if self.all_results else 0
            ),
            total_time_seconds=total_time,
            requests_per_second=(
                len(self.all_results) / total_time if total_time > 0 else 0
            ),
            avg_response_time_ms=(
                statistics.mean(response_times) if response_times else 0
            ),
            median_response_time_ms=(
                statistics.median(response_times) if response_times else 0
            ),
            p95_response_time_ms=(
                sorted(response_times)[int(len(response_times) * 0.95)]
                if response_times
                else 0
            ),
            p99_response_time_ms=(
                sorted(response_times)[int(len(response_times) * 0.99)]
                if response_times
                else 0
            ),
            min_response_time_ms=min(response_times) if response_times else 0,
            max_response_time_ms=max(response_times) if response_times else 0,
            by_request_type=by_type_summary,
            errors=errors,
        )

    def _print_summary(self, summary: TestSummary):
        """Print test summary"""
        print(f"\n{'='*70}")
        print(f"📊 TEST SUMMARY")
        print(f"{'='*70}")

        print(f"\n🎯 Overall Results:")
        print(f"   • Total Users: {summary.total_users}")
        print(f"   • Total Requests: {summary.total_requests}")
        print(
            f"   • Successful: {summary.successful_requests} ({summary.success_rate*100:.1f}%)"
        )
        print(f"   • Failed: {summary.failed_requests}")
        print(f"   • Total Time: {summary.total_time_seconds:.2f}s")
        print(f"   • Throughput: {summary.requests_per_second:.2f} req/s")

        print(f"\n⏱️  Response Times:")
        print(f"   • Average: {summary.avg_response_time_ms:.2f}ms")
        print(f"   • Median: {summary.median_response_time_ms:.2f}ms")
        print(f"   • P95: {summary.p95_response_time_ms:.2f}ms")
        print(f"   • P99: {summary.p99_response_time_ms:.2f}ms")
        print(f"   • Min: {summary.min_response_time_ms:.2f}ms")
        print(f"   • Max: {summary.max_response_time_ms:.2f}ms")

        print(f"\n📋 By Request Type:")
        print(
            f"   {'Type':<25} {'Success':<10} {'Failed':<10} {'Avg Time':<12} {'Rate':<10}"
        )
        print(f"   {'-'*67}")
        for req_type, data in summary.by_request_type.items():
            print(
                f"   {req_type:<25} {data['success']:<10} {data['failed']:<10} "
                f"{data['avg_time_ms']:.0f}ms{' ':<6} {data['success_rate']*100:.1f}%"
            )

        if summary.errors:
            print(f"\n❌ Sample Errors (first {len(summary.errors)}):")
            for err in summary.errors[:5]:
                print(
                    f"   • User {err['user_id']}: {err['request_type']} - {err['error']}"
                )

        print(f"\n{'='*70}")

    def save_results(self, filepath: str):
        """Save detailed results to JSON file"""
        results_data = {
            "test_time": datetime.now().isoformat(),
            "config": {"num_users": self.num_users, "base_url": self.base_url},
            "results": [asdict(r) for r in self.all_results],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)

        print(f"\n📁 Detailed results saved to: {filepath}")


# =============================================================================
# MAIN
# =============================================================================


async def main():
    parser = argparse.ArgumentParser(
        description="Run authenticated multi-user performance test"
    )
    parser.add_argument(
        "--users", "-u", type=int, default=100, help="Number of users (default: 100)"
    )
    parser.add_argument(
        "--requests", "-r", type=int, default=10, help="Requests per user (default: 10)"
    )
    parser.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=20,
        help="Concurrent batch size (default: 20)",
    )
    parser.add_argument(
        "--min-delay",
        type=float,
        default=0.5,
        help="Minimum delay between requests in seconds (default: 0.5)",
    )
    parser.add_argument(
        "--max-delay",
        type=float,
        default=2.0,
        help="Maximum delay between requests in seconds (default: 2.0)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file for detailed results (JSON)",
    )
    parser.add_argument(
        "--url",
        type=str,
        default=API_BASE_URL,
        help=f"API base URL (default: {API_BASE_URL})",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging for each request",
    )

    args = parser.parse_args()

    tester = AuthenticatedPerformanceTester(
        base_url=args.url, num_users=args.users, verbose=args.verbose
    )

    summary = await tester.run_test(
        requests_per_user=args.requests,
        delay_range=(args.min_delay, args.max_delay),
        concurrent_batch_size=args.batch_size,
    )

    if args.output and summary:
        tester.save_results(args.output)

    return summary


if __name__ == "__main__":
    asyncio.run(main())
