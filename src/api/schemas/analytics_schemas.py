"""
Analytics Schemas - Dashboard API Response Models
Pydantic schemas for analytics and dashboard data
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from datetime import date as date_type
from uuid import UUID
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================


class TimePeriod(str, Enum):
    """Time period for analytics aggregation"""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    ALL_TIME = "all_time"


class RAGMode(str, Enum):
    """RAG processing modes"""

    FAST = "fast"
    BALANCED = "balanced"
    QUALITY = "quality"
    # NOTE: ADAPTIVE removed - use BALANCED as default


# =============================================================================
# 1. COST OVERVIEW SCHEMAS
# =============================================================================


class TokenBreakdown(BaseModel):
    """Token usage breakdown"""

    input_tokens: int = Field(0, description="Total input/prompt tokens")
    output_tokens: int = Field(0, description="Total output/completion tokens")
    total_tokens: int = Field(0, description="Total tokens (input + output)")


class DailyTokenUsage(BaseModel):
    """Daily token usage data point"""

    usage_date: date_type = Field(..., alias="date", description="Date (YYYY-MM-DD)")
    input_tokens: int = Field(0, description="Input tokens for the day")
    output_tokens: int = Field(0, description="Output tokens for the day")
    total_tokens: int = Field(0, description="Total tokens for the day")
    cost_usd: float = Field(0.0, description="Cost in USD for the day")
    query_count: int = Field(0, description="Number of queries for the day")

    model_config = {"populate_by_name": True}


class CostOverviewResponse(BaseModel):
    """
    Cost overview response

    Tổng quan chi phí: Total Cost, Token breakdown, Average cost per query
    """

    total_cost_usd: float = Field(0.0, description="Total cost in USD")
    token_breakdown: TokenBreakdown = Field(
        default_factory=TokenBreakdown, description="Token usage breakdown"
    )
    average_cost_per_query: float = Field(
        0.0, description="Average cost per query in USD"
    )
    total_queries: int = Field(0, description="Total number of queries")
    total_conversations: int = Field(0, description="Total number of conversations")
    period: str = Field(
        ..., description="Period for the data (e.g., '2026-01', 'all_time')"
    )
    period_start: Optional[date_type] = Field(None, description="Period start date")
    period_end: Optional[date_type] = Field(None, description="Period end date")

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_cost_usd": 125.50,
                "token_breakdown": {
                    "input_tokens": 2000000,
                    "output_tokens": 500000,
                    "total_tokens": 2500000,
                },
                "average_cost_per_query": 0.015,
                "total_queries": 8367,
                "total_conversations": 450,
                "period": "2026-01",
                "period_start": "2026-01-01",
                "period_end": "2026-01-31",
            }
        }
    }


class DailyTokenUsageResponse(BaseModel):
    """Daily token usage over time - for line charts"""

    data: List[DailyTokenUsage] = Field(
        default_factory=list, description="Daily token usage data"
    )
    total_days: int = Field(0, description="Number of days in the response")
    start_date: date_type = Field(..., description="Start date of the range")
    end_date: date_type = Field(..., description="End date of the range")


class UserCostInfo(BaseModel):
    """Cost information for a single user"""

    user_id: UUID = Field(..., description="User UUID")
    email: str = Field(..., description="User email")
    full_name: Optional[str] = Field(None, description="User full name")
    total_cost_usd: float = Field(0.0, description="Total cost in USD")
    total_tokens: int = Field(0, description="Total tokens consumed")
    total_queries: int = Field(0, description="Total queries made")
    total_messages: int = Field(0, description="Total messages sent")
    rank: int = Field(..., description="Rank by cost (1 = highest)")


class CostPerUserResponse(BaseModel):
    """
    Cost per user response

    Top users by cost consumption
    """

    top_users: List[UserCostInfo] = Field(
        default_factory=list, description="Top users by cost"
    )
    total_users: int = Field(0, description="Total number of users")
    total_cost_all_users: float = Field(0.0, description="Total cost across all users")
    period: str = Field(..., description="Period for the data")


# =============================================================================
# 1.5 ACTIVE USERS DETAIL SCHEMAS (Dashboard Dialog)
# =============================================================================


class ActiveUserDetail(BaseModel):
    """Detail information for an active user"""

    user_id: UUID = Field(..., description="User UUID")
    email: str = Field(..., description="User email")
    full_name: Optional[str] = Field(None, description="User full name")
    last_active_at: datetime = Field(..., description="Last activity timestamp")
    queries_count: int = Field(0, description="Number of queries in period")
    total_tokens: int = Field(0, description="Total tokens consumed in period")
    cost_usd: float = Field(0.0, description="Cost in USD for period")
    conversations_count: int = Field(0, description="Number of conversations in period")


class ActiveUsersResponse(BaseModel):
    """
    Active users detail response

    List of active users with their usage metrics
    """

    period: str = Field("day", description="Period: day, week, month")
    active_users: List[ActiveUserDetail] = Field(
        default_factory=list, description="List of active users with details"
    )
    total_active: int = Field(0, description="Total active users count")
    total_cost: float = Field(0.0, description="Total cost for all active users")
    total_tokens: int = Field(0, description="Total tokens for all active users")
    total_queries: int = Field(0, description="Total queries for all active users")


# =============================================================================
# 1.6 ZERO CITATION MESSAGES SCHEMAS (Dashboard Dialog)
# =============================================================================


class ZeroCitationMessage(BaseModel):
    """Message without citations (potential hallucination)"""

    message_id: UUID = Field(..., description="Message UUID")
    conversation_id: UUID = Field(..., description="Conversation UUID")
    user_email: str = Field(..., description="User email who asked")
    question: str = Field(..., description="User question (previous message)")
    answer: str = Field(..., description="Assistant answer without citations")
    rag_mode: Optional[str] = Field(None, description="RAG mode used")
    created_at: datetime = Field(..., description="Message timestamp")
    processing_time_ms: Optional[int] = Field(None, description="Processing time")


class ZeroCitationResponse(BaseModel):
    """
    Zero citation messages response

    List of assistant messages that have no citations
    """

    messages: List[ZeroCitationMessage] = Field(
        default_factory=list, description="Messages without citations"
    )
    total_count: int = Field(0, description="Total zero-citation messages")
    period: str = Field(..., description="Period for the data")
    zero_citation_rate: float = Field(0.0, description="Rate of zero-citation messages")


# =============================================================================
# 1.7 QUERIES BY CATEGORY SCHEMAS (Phase 3 Analytics)
# =============================================================================


class CategoryQueryCount(BaseModel):
    """Query count by category"""

    category: str = Field(..., description="Category name")
    query_count: int = Field(0, description="Number of queries for this category")
    percentage: float = Field(0.0, description="Percentage of total queries")
    avg_latency_ms: float = Field(0.0, description="Average latency for this category")


class QueriesByCategoryResponse(BaseModel):
    """
    Queries by category response

    Shows which document categories are queried most frequently
    """

    categories: List[CategoryQueryCount] = Field(
        default_factory=list, description="Query counts per category"
    )
    total_queries: int = Field(0, description="Total queries analyzed")
    period: str = Field(..., description="Period for the data")


# =============================================================================
# 2. KNOWLEDGE BASE HEALTH SCHEMAS
# =============================================================================


class CategoryDistribution(BaseModel):
    """Document distribution by category"""

    category: str = Field(..., description="Category name")
    count: int = Field(0, description="Number of documents")
    percentage: float = Field(0.0, description="Percentage of total")


class DocumentIssue(BaseModel):
    """Document with issues (not active status)"""

    document_id: Optional[str] = Field(None, description="Document ID")
    document_uuid: UUID = Field(..., description="Document UUID")
    filename: Optional[str] = Field(None, description="Original filename")
    document_name: Optional[str] = Field(None, description="Document name")
    status: str = Field(..., description="Current status")
    category: Optional[str] = Field(None, description="Category")
    created_at: Optional[datetime] = Field(None, description="Creation time")
    error_message: Optional[str] = Field(None, description="Error message if any")


class KnowledgeBaseHealthResponse(BaseModel):
    """
    Knowledge Base Health response

    Sức khỏe kho dữ liệu: Active documents, categories distribution, chunk count
    """

    total_documents: int = Field(0, description="Total documents in system")
    total_active_documents: int = Field(0, description="Documents with status='active'")
    documents_by_category: List[CategoryDistribution] = Field(
        default_factory=list, description="Document distribution by category"
    )
    documents_by_type: Dict[str, int] = Field(
        default_factory=dict, description="Document count by type (law, decree, etc.)"
    )
    documents_by_status: Dict[str, int] = Field(
        default_factory=dict, description="Document count by status"
    )
    total_chunks: int = Field(0, description="Total number of document chunks")
    average_chunks_per_document: float = Field(
        0.0, description="Average chunks per document"
    )
    upload_issues: List[DocumentIssue] = Field(
        default_factory=list,
        description="Documents with non-active status (errors, processing)",
    )
    last_upload_at: Optional[datetime] = Field(
        None, description="Last document upload time"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_documents": 200,
                "total_active_documents": 185,
                "documents_by_category": [
                    {"category": "Luat chinh", "count": 50, "percentage": 25.0},
                    {"category": "Nghi dinh", "count": 45, "percentage": 22.5},
                ],
                "documents_by_type": {"law": 50, "decree": 45, "circular": 30},
                "documents_by_status": {"active": 185, "processing": 10, "error": 5},
                "total_chunks": 15000,
                "average_chunks_per_document": 75.0,
                "upload_issues": [],
                "last_upload_at": "2026-01-10T10:30:00",
            }
        }
    }


# =============================================================================
# 3. RAG SYSTEM PERFORMANCE SCHEMAS
# =============================================================================


class RAGModeDistribution(BaseModel):
    """Distribution of RAG mode usage"""

    mode: str = Field(..., description="RAG mode name")
    count: int = Field(0, description="Number of queries using this mode")
    percentage: float = Field(0.0, description="Percentage of total queries")


class LatencyPercentiles(BaseModel):
    """Latency percentile breakdown"""

    p50: float = Field(0.0, description="50th percentile (median) latency in ms")
    p75: float = Field(0.0, description="75th percentile latency in ms")
    p90: float = Field(0.0, description="90th percentile latency in ms")
    p95: float = Field(0.0, description="95th percentile latency in ms")
    p99: float = Field(0.0, description="99th percentile latency in ms")


class RAGPerformanceResponse(BaseModel):
    """
    RAG System Performance response

    Hiệu năng hệ thống RAG: Latency, RAG mode distribution, Retrieval rate
    """

    average_latency_ms: float = Field(
        0.0, description="Average total latency in milliseconds"
    )
    latency_percentiles: LatencyPercentiles = Field(
        default_factory=LatencyPercentiles, description="Latency percentile breakdown"
    )
    rag_mode_distribution: List[RAGModeDistribution] = Field(
        default_factory=list, description="Distribution of RAG mode usage"
    )
    average_retrieval_count: float = Field(
        0.0, description="Average chunks retrieved per query"
    )
    total_queries_analyzed: int = Field(0, description="Total queries in the analysis")
    queries_with_retrieval: int = Field(
        0, description="Queries that had retrieval results"
    )

    # Performance by mode
    latency_by_mode: Dict[str, float] = Field(
        default_factory=dict, description="Average latency per RAG mode"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "average_latency_ms": 2350.5,
                "latency_percentiles": {
                    "p50": 2100.0,
                    "p75": 2800.0,
                    "p90": 3500.0,
                    "p95": 4200.0,
                    "p99": 5500.0,
                },
                "rag_mode_distribution": [
                    {"mode": "balanced", "count": 650, "percentage": 65.0},
                    {"mode": "fast", "count": 200, "percentage": 20.0},
                    {"mode": "quality", "count": 150, "percentage": 15.0},
                ],
                "average_retrieval_count": 4.2,
                "total_queries_analyzed": 1000,
                "queries_with_retrieval": 950,
                "latency_by_mode": {
                    "fast": 1200.0,
                    "balanced": 2500.0,
                    "quality": 4000.0,
                },
            }
        }
    }


# =============================================================================
# 4. QUALITY & FEEDBACK SCHEMAS
# =============================================================================


class RecentFeedback(BaseModel):
    """Recent feedback comment"""

    feedback_id: UUID = Field(..., description="Feedback UUID")
    user_email: Optional[str] = Field(None, description="User who gave feedback")
    message_id: UUID = Field(..., description="Message that was rated")
    rating: int = Field(..., description="Rating value")
    feedback_type: Optional[str] = Field(None, description="Type of feedback")
    comment: Optional[str] = Field(None, description="User comment")
    created_at: datetime = Field(..., description="Feedback timestamp")


class RatingDistribution(BaseModel):
    """Distribution of ratings"""

    rating: int = Field(..., description="Rating value (1-5 or -1/1)")
    count: int = Field(0, description="Number of feedbacks with this rating")
    percentage: float = Field(0.0, description="Percentage of total")


class QualityFeedbackResponse(BaseModel):
    """
    Quality & Feedback response

    Chất lượng & Phản hồi: CSAT score, negative rate, recent comments, zero-citation rate
    """

    csat_score: Optional[float] = Field(
        None, description="Customer Satisfaction Score (1-5 average)"
    )
    total_feedbacks: int = Field(0, description="Total feedback count")
    positive_feedbacks: int = Field(
        0, description="Feedbacks with rating >= 4 or thumbs up"
    )
    negative_feedbacks: int = Field(
        0, description="Feedbacks with rating <= 2 or thumbs down"
    )
    negative_feedback_rate: float = Field(
        0.0, description="Percentage of negative feedbacks"
    )

    rating_distribution: List[RatingDistribution] = Field(
        default_factory=list, description="Distribution of ratings"
    )

    # Citation analysis
    total_assistant_messages: int = Field(
        0, description="Total assistant messages analyzed"
    )
    messages_with_citations: int = Field(0, description="Messages that have citations")
    zero_citation_count: int = Field(
        0, description="Messages with no citations (potential hallucination)"
    )
    zero_citation_rate: float = Field(
        0.0, description="Percentage of zero-citation answers"
    )

    # Recent feedback
    recent_comments: List[RecentFeedback] = Field(
        default_factory=list, description="Most recent feedback comments"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "csat_score": 4.2,
                "total_feedbacks": 350,
                "positive_feedbacks": 280,
                "negative_feedbacks": 42,
                "negative_feedback_rate": 0.12,
                "rating_distribution": [
                    {"rating": 5, "count": 150, "percentage": 42.9},
                    {"rating": 4, "count": 130, "percentage": 37.1},
                ],
                "total_assistant_messages": 5000,
                "messages_with_citations": 4600,
                "zero_citation_count": 400,
                "zero_citation_rate": 0.08,
                "recent_comments": [],
            }
        }
    }


# =============================================================================
# 5. USER ENGAGEMENT SCHEMAS
# =============================================================================


class TopQuery(BaseModel):
    """Top searched query"""

    query_text: str = Field(..., description="Query text (truncated)")
    count: int = Field(0, description="Number of times queried")
    unique_users: int = Field(0, description="Number of unique users")


class EngagementTrend(BaseModel):
    """Daily engagement data point"""

    trend_date: date_type = Field(..., alias="date", description="Date")
    active_users: int = Field(0, description="Active users on this day")
    total_queries: int = Field(0, description="Total queries on this day")
    total_conversations: int = Field(0, description="New conversations on this day")

    model_config = {"populate_by_name": True}


class UserEngagementResponse(BaseModel):
    """
    User Engagement response

    Hành vi người dùng: DAU/MAU, top queries, engagement trends
    """

    # Active users
    dau: int = Field(0, description="Daily Active Users (today)")
    wau: int = Field(0, description="Weekly Active Users (last 7 days)")
    mau: int = Field(0, description="Monthly Active Users (last 30 days)")
    total_registered_users: int = Field(0, description="Total registered users")

    # Engagement ratios
    dau_mau_ratio: float = Field(0.0, description="DAU/MAU ratio (stickiness)")

    # Activity metrics
    avg_queries_per_user: float = Field(
        0.0, description="Average queries per active user"
    )
    avg_conversations_per_user: float = Field(
        0.0, description="Average conversations per active user"
    )

    # Top queries
    top_queries: List[TopQuery] = Field(
        default_factory=list, description="Most frequently asked queries"
    )

    # Trends
    engagement_trend: List[EngagementTrend] = Field(
        default_factory=list, description="Daily engagement trend (last 30 days)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "dau": 45,
                "wau": 95,
                "mau": 120,
                "total_registered_users": 200,
                "dau_mau_ratio": 0.375,
                "avg_queries_per_user": 8.5,
                "avg_conversations_per_user": 2.3,
                "top_queries": [
                    {
                        "query_text": "Điều kiện tham gia đấu thầu",
                        "count": 25,
                        "unique_users": 15,
                    }
                ],
                "engagement_trend": [],
            }
        }
    }


# =============================================================================
# 6. DASHBOARD SUMMARY SCHEMA (Combined)
# =============================================================================


class DashboardSummaryResponse(BaseModel):
    """
    Dashboard Summary - Combined overview of all metrics

    Single endpoint to get all dashboard data at once
    """

    # Timestamps
    generated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Report generation time"
    )
    period: str = Field("current_month", description="Period for the data")

    # Key metrics (quick overview)
    key_metrics: Dict[str, Any] = Field(
        default_factory=dict, description="Key metrics for quick overview"
    )

    # Detailed sections
    cost_overview: Optional[CostOverviewResponse] = Field(
        None, description="Cost overview data"
    )
    knowledge_base: Optional[KnowledgeBaseHealthResponse] = Field(
        None, description="Knowledge base health"
    )
    rag_performance: Optional[RAGPerformanceResponse] = Field(
        None, description="RAG performance metrics"
    )
    quality_feedback: Optional[QualityFeedbackResponse] = Field(
        None, description="Quality and feedback data"
    )
    user_engagement: Optional[UserEngagementResponse] = Field(
        None, description="User engagement metrics"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "generated_at": "2026-01-10T12:00:00",
                "period": "2026-01",
                "key_metrics": {
                    "total_cost_usd": 125.50,
                    "active_users_today": 45,
                    "avg_latency_ms": 2350,
                    "csat_score": 4.2,
                    "total_documents": 185,
                },
                "cost_overview": None,
                "knowledge_base": None,
                "rag_performance": None,
                "quality_feedback": None,
                "user_engagement": None,
            }
        }
    }


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================


class AnalyticsQueryParams(BaseModel):
    """Common query parameters for analytics endpoints"""

    period: TimePeriod = Field(
        TimePeriod.MONTH, description="Time period for aggregation"
    )
    start_date: Optional[date_type] = Field(None, description="Custom start date")
    end_date: Optional[date_type] = Field(None, description="Custom end date")


class TopUsersQueryParams(BaseModel):
    """Query parameters for top users endpoint"""

    limit: int = Field(10, ge=1, le=100, description="Number of top users to return")
    period: TimePeriod = Field(
        TimePeriod.MONTH, description="Time period for aggregation"
    )
