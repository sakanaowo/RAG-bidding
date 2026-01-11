"""
Tests for Analytics Schemas
Unit tests for Pydantic schemas validation
"""

import pytest
from datetime import date, datetime
from uuid import uuid4

from src.api.schemas.analytics_schemas import (
    TimePeriod,
    TokenBreakdown,
    DailyTokenUsage,
    CostOverviewResponse,
    DailyTokenUsageResponse,
    UserCostInfo,
    CostPerUserResponse,
    CategoryDistribution,
    DocumentIssue,
    KnowledgeBaseHealthResponse,
    RAGModeDistribution,
    LatencyPercentiles,
    RAGPerformanceResponse,
    RatingDistribution,
    RecentFeedback,
    QualityFeedbackResponse,
    TopQuery,
    EngagementTrend,
    UserEngagementResponse,
    DashboardSummaryResponse,
)


class TestTimePeriodEnum:
    """Tests for TimePeriod enum"""

    def test_all_periods_defined(self):
        """Test all expected periods are defined"""
        assert TimePeriod.DAY == "day"
        assert TimePeriod.WEEK == "week"
        assert TimePeriod.MONTH == "month"
        assert TimePeriod.QUARTER == "quarter"
        assert TimePeriod.YEAR == "year"
        assert TimePeriod.ALL_TIME == "all_time"


class TestTokenBreakdown:
    """Tests for TokenBreakdown schema"""

    def test_default_values(self):
        """Test default values are zeros"""
        breakdown = TokenBreakdown()
        assert breakdown.input_tokens == 0
        assert breakdown.output_tokens == 0
        assert breakdown.total_tokens == 0

    def test_with_values(self):
        """Test with provided values"""
        breakdown = TokenBreakdown(
            input_tokens=1000, output_tokens=500, total_tokens=1500
        )
        assert breakdown.input_tokens == 1000
        assert breakdown.output_tokens == 500
        assert breakdown.total_tokens == 1500


class TestDailyTokenUsage:
    """Tests for DailyTokenUsage schema"""

    def test_required_date(self):
        """Test date is required"""
        usage = DailyTokenUsage(date=date.today())
        assert usage.usage_date == date.today()
        assert usage.input_tokens == 0
        assert usage.cost_usd == 0.0

    def test_full_usage_data(self):
        """Test with all fields populated"""
        today = date.today()
        usage = DailyTokenUsage(
            date=today,
            input_tokens=5000,
            output_tokens=1000,
            total_tokens=6000,
            cost_usd=0.025,
            query_count=50,
        )
        assert usage.usage_date == today
        assert usage.input_tokens == 5000
        assert usage.output_tokens == 1000
        assert usage.total_tokens == 6000
        assert usage.cost_usd == 0.025
        assert usage.query_count == 50


class TestCostOverviewResponse:
    """Tests for CostOverviewResponse schema"""

    def test_minimal_response(self):
        """Test minimal valid response"""
        response = CostOverviewResponse(period="2026-01")
        assert response.total_cost_usd == 0.0
        assert response.period == "2026-01"
        assert isinstance(response.token_breakdown, TokenBreakdown)

    def test_full_response(self):
        """Test full response with all fields"""
        response = CostOverviewResponse(
            total_cost_usd=125.50,
            token_breakdown=TokenBreakdown(
                input_tokens=2000000, output_tokens=500000, total_tokens=2500000
            ),
            average_cost_per_query=0.015,
            total_queries=8367,
            total_conversations=450,
            period="2026-01",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
        )
        assert response.total_cost_usd == 125.50
        assert response.token_breakdown.total_tokens == 2500000
        assert response.average_cost_per_query == 0.015


class TestUserCostInfo:
    """Tests for UserCostInfo schema"""

    def test_user_cost_info(self):
        """Test user cost info creation"""
        user_id = uuid4()
        info = UserCostInfo(
            user_id=user_id,
            email="test@example.com",
            full_name="Test User",
            total_cost_usd=25.50,
            total_tokens=100000,
            total_queries=500,
            total_messages=1000,
            rank=1,
        )
        assert info.user_id == user_id
        assert info.email == "test@example.com"
        assert info.rank == 1


class TestCategoryDistribution:
    """Tests for CategoryDistribution schema"""

    def test_category_distribution(self):
        """Test category distribution creation"""
        dist = CategoryDistribution(category="Luat chinh", count=50, percentage=25.0)
        assert dist.category == "Luat chinh"
        assert dist.count == 50
        assert dist.percentage == 25.0


class TestDocumentIssue:
    """Tests for DocumentIssue schema"""

    def test_document_issue(self):
        """Test document issue creation"""
        doc_uuid = uuid4()
        issue = DocumentIssue(
            document_uuid=doc_uuid,
            document_id="DOC-001",
            filename="test.pdf",
            status="processing",
        )
        assert issue.document_uuid == doc_uuid
        assert issue.status == "processing"


class TestKnowledgeBaseHealthResponse:
    """Tests for KnowledgeBaseHealthResponse schema"""

    def test_default_response(self):
        """Test default response values"""
        response = KnowledgeBaseHealthResponse()
        assert response.total_documents == 0
        assert response.total_active_documents == 0
        assert response.documents_by_category == []
        assert response.total_chunks == 0

    def test_full_response(self):
        """Test full response"""
        response = KnowledgeBaseHealthResponse(
            total_documents=200,
            total_active_documents=185,
            documents_by_category=[
                CategoryDistribution(category="Luat chinh", count=50, percentage=25.0)
            ],
            total_chunks=15000,
            average_chunks_per_document=75.0,
        )
        assert response.total_documents == 200
        assert len(response.documents_by_category) == 1


class TestRAGModeDistribution:
    """Tests for RAGModeDistribution schema"""

    def test_mode_distribution(self):
        """Test RAG mode distribution"""
        dist = RAGModeDistribution(mode="balanced", count=650, percentage=65.0)
        assert dist.mode == "balanced"
        assert dist.count == 650
        assert dist.percentage == 65.0


class TestLatencyPercentiles:
    """Tests for LatencyPercentiles schema"""

    def test_default_percentiles(self):
        """Test default percentile values"""
        percentiles = LatencyPercentiles()
        assert percentiles.p50 == 0.0
        assert percentiles.p95 == 0.0
        assert percentiles.p99 == 0.0

    def test_with_values(self):
        """Test with provided values"""
        percentiles = LatencyPercentiles(
            p50=2100.0, p75=2800.0, p90=3500.0, p95=4200.0, p99=5500.0
        )
        assert percentiles.p50 == 2100.0
        assert percentiles.p99 == 5500.0


class TestRAGPerformanceResponse:
    """Tests for RAGPerformanceResponse schema"""

    def test_default_response(self):
        """Test default response values"""
        response = RAGPerformanceResponse()
        assert response.average_latency_ms == 0.0
        assert response.rag_mode_distribution == []
        assert response.average_retrieval_count == 0.0

    def test_full_response(self):
        """Test full response"""
        response = RAGPerformanceResponse(
            average_latency_ms=2350.5,
            latency_percentiles=LatencyPercentiles(
                p50=2100.0, p75=2800.0, p90=3500.0, p95=4200.0, p99=5500.0
            ),
            rag_mode_distribution=[
                RAGModeDistribution(mode="balanced", count=650, percentage=65.0)
            ],
            average_retrieval_count=4.2,
            total_queries_analyzed=1000,
        )
        assert response.average_latency_ms == 2350.5
        assert len(response.rag_mode_distribution) == 1


class TestRatingDistribution:
    """Tests for RatingDistribution schema"""

    def test_rating_distribution(self):
        """Test rating distribution"""
        dist = RatingDistribution(rating=5, count=150, percentage=42.9)
        assert dist.rating == 5
        assert dist.count == 150


class TestRecentFeedback:
    """Tests for RecentFeedback schema"""

    def test_recent_feedback(self):
        """Test recent feedback creation"""
        feedback_id = uuid4()
        message_id = uuid4()
        now = datetime.utcnow()

        feedback = RecentFeedback(
            feedback_id=feedback_id,
            user_email="user@example.com",
            message_id=message_id,
            rating=5,
            feedback_type="helpfulness",
            comment="Very helpful response!",
            created_at=now,
        )
        assert feedback.feedback_id == feedback_id
        assert feedback.rating == 5
        assert feedback.comment == "Very helpful response!"


class TestQualityFeedbackResponse:
    """Tests for QualityFeedbackResponse schema"""

    def test_default_response(self):
        """Test default response values"""
        response = QualityFeedbackResponse()
        assert response.csat_score is None
        assert response.total_feedbacks == 0
        assert response.negative_feedback_rate == 0.0
        assert response.zero_citation_rate == 0.0

    def test_full_response(self):
        """Test full response"""
        response = QualityFeedbackResponse(
            csat_score=4.2,
            total_feedbacks=350,
            positive_feedbacks=280,
            negative_feedbacks=42,
            negative_feedback_rate=0.12,
            zero_citation_count=400,
            zero_citation_rate=0.08,
        )
        assert response.csat_score == 4.2
        assert response.negative_feedback_rate == 0.12


class TestTopQuery:
    """Tests for TopQuery schema"""

    def test_top_query(self):
        """Test top query creation"""
        query = TopQuery(
            query_text="Điều kiện tham gia đấu thầu", count=25, unique_users=15
        )
        assert query.query_text == "Điều kiện tham gia đấu thầu"
        assert query.count == 25


class TestEngagementTrend:
    """Tests for EngagementTrend schema"""

    def test_engagement_trend(self):
        """Test engagement trend creation"""
        trend = EngagementTrend(
            date=date.today(),
            active_users=45,
            total_queries=200,
            total_conversations=30,
        )
        assert trend.active_users == 45
        assert trend.total_queries == 200


class TestUserEngagementResponse:
    """Tests for UserEngagementResponse schema"""

    def test_default_response(self):
        """Test default response values"""
        response = UserEngagementResponse()
        assert response.dau == 0
        assert response.mau == 0
        assert response.dau_mau_ratio == 0.0
        assert response.top_queries == []

    def test_full_response(self):
        """Test full response"""
        response = UserEngagementResponse(
            dau=45,
            wau=95,
            mau=120,
            total_registered_users=200,
            dau_mau_ratio=0.375,
            avg_queries_per_user=8.5,
            top_queries=[TopQuery(query_text="Test query", count=25, unique_users=15)],
        )
        assert response.dau == 45
        assert response.dau_mau_ratio == 0.375
        assert len(response.top_queries) == 1


class TestDashboardSummaryResponse:
    """Tests for DashboardSummaryResponse schema"""

    def test_default_response(self):
        """Test default response values"""
        response = DashboardSummaryResponse()
        assert response.period == "current_month"
        assert response.key_metrics == {}
        assert response.cost_overview is None

    def test_with_key_metrics(self):
        """Test with key metrics"""
        response = DashboardSummaryResponse(
            period="2026-01",
            key_metrics={"total_cost_usd": 125.50, "dau": 45, "csat_score": 4.2},
        )
        assert response.key_metrics["total_cost_usd"] == 125.50
        assert response.key_metrics["dau"] == 45
