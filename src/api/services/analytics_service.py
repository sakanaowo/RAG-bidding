"""
Analytics Service - Dashboard Business Logic
Calculates metrics from database for analytics dashboard
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, distinct, case, text
from sqlalchemy.sql import extract

from src.models.users import User
from src.models.conversations import Conversation
from src.models.messages import Message
from src.models.queries import Query
from src.models.feedback import Feedback
from src.models.citations import Citation
from src.models.documents import Document
from src.models.document_chunks import DocumentChunk
from src.models.user_metrics import UserUsageMetric

from src.api.schemas.analytics_schemas import (
    TimePeriod,
    CostOverviewResponse,
    TokenBreakdown,
    DailyTokenUsage,
    DailyTokenUsageResponse,
    UserCostInfo,
    CostPerUserResponse,
    KnowledgeBaseHealthResponse,
    CategoryDistribution,
    DocumentIssue,
    RAGPerformanceResponse,
    RAGModeDistribution,
    LatencyPercentiles,
    QualityFeedbackResponse,
    RatingDistribution,
    RecentFeedback,
    UserEngagementResponse,
    TopQuery,
    EngagementTrend,
    DashboardSummaryResponse,
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Analytics service for dashboard metrics calculation.

    Provides methods to calculate:
    1. Cost Overview (total cost, token breakdown, cost per query)
    2. Knowledge Base Health (documents, categories, chunks)
    3. RAG Performance (latency, mode distribution, retrieval rate)
    4. Quality & Feedback (CSAT, negative rate, zero-citation)
    5. User Engagement (DAU/MAU, top queries)
    """

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    @staticmethod
    def _get_date_range(
        period: TimePeriod,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Tuple[date, date, str]:
        """
        Calculate date range based on period or custom dates.

        Returns:
            Tuple of (start_date, end_date, period_label)
        """
        today = date.today()

        if start_date and end_date:
            return start_date, end_date, f"{start_date}_{end_date}"

        if period == TimePeriod.DAY:
            return today, today, today.isoformat()
        elif period == TimePeriod.WEEK:
            start = today - timedelta(days=7)
            return start, today, f"week_{today.isocalendar()[1]}"
        elif period == TimePeriod.MONTH:
            start = today.replace(day=1)
            return start, today, today.strftime("%Y-%m")
        elif period == TimePeriod.QUARTER:
            quarter = (today.month - 1) // 3
            start = today.replace(month=quarter * 3 + 1, day=1)
            return start, today, f"{today.year}_Q{quarter + 1}"
        elif period == TimePeriod.YEAR:
            start = today.replace(month=1, day=1)
            return start, today, str(today.year)
        else:  # ALL_TIME
            return date(2020, 1, 1), today, "all_time"

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        """Safely convert value to float"""
        if value is None:
            return default
        try:
            if isinstance(value, Decimal):
                return float(value)
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        """Safely convert value to int"""
        if value is None:
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    # =========================================================================
    # 1. COST OVERVIEW
    # =========================================================================

    @staticmethod
    def get_cost_overview(
        db: Session,
        period: TimePeriod = TimePeriod.MONTH,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> CostOverviewResponse:
        """
        Get cost overview metrics.

        Data sources:
        - Query table: estimated_cost_usd, tokens_total
        - UserUsageMetric table: aggregated daily data
        - Conversation table: total_cost_usd
        """
        start, end, period_label = AnalyticsService._get_date_range(
            period, start_date, end_date
        )

        # Convert dates to datetime for comparison
        start_dt = datetime.combine(start, datetime.min.time())
        end_dt = datetime.combine(end, datetime.max.time())

        # Get totals from queries table (most accurate)
        # Now using actual input_tokens and output_tokens columns
        query_stats = (
            db.query(
                func.sum(Query.estimated_cost_usd).label("total_cost"),
                func.sum(Query.tokens_total).label("total_tokens"),
                func.sum(Query.input_tokens).label("input_tokens"),
                func.sum(Query.output_tokens).label("output_tokens"),
                func.count(Query.id).label("query_count"),
            )
            .filter(and_(Query.created_at >= start_dt, Query.created_at <= end_dt))
            .first()
        )

        total_cost = AnalyticsService._safe_float(query_stats.total_cost)
        total_tokens = AnalyticsService._safe_int(query_stats.total_tokens)
        query_count = AnalyticsService._safe_int(query_stats.query_count)

        # Use actual input/output tokens if available, fallback to estimation
        input_tokens = AnalyticsService._safe_int(query_stats.input_tokens)
        output_tokens = AnalyticsService._safe_int(query_stats.output_tokens)

        # Fallback to 80/20 estimation if separate tracking not available
        if input_tokens == 0 and output_tokens == 0 and total_tokens > 0:
            input_tokens = int(total_tokens * 0.8)
            output_tokens = total_tokens - input_tokens

        # Get conversation count
        conv_count = (
            db.query(func.count(Conversation.id))
            .filter(
                and_(
                    Conversation.created_at >= start_dt,
                    Conversation.created_at <= end_dt,
                )
            )
            .scalar()
            or 0
        )

        # Calculate average cost per query
        avg_cost = total_cost / query_count if query_count > 0 else 0.0

        return CostOverviewResponse(
            total_cost_usd=round(total_cost, 4),
            token_breakdown=TokenBreakdown(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
            ),
            average_cost_per_query=round(avg_cost, 6),
            total_queries=query_count,
            total_conversations=conv_count,
            period=period_label,
            period_start=start,
            period_end=end,
        )

    @staticmethod
    def get_daily_token_usage(
        db: Session, start_date: date, end_date: date
    ) -> DailyTokenUsageResponse:
        """
        Get daily token usage for chart visualization.

        Returns daily breakdown of tokens and cost.
        """
        # Query from UserUsageMetric (already aggregated by day)
        # Now using actual input/output token columns
        daily_metrics = (
            db.query(
                UserUsageMetric.date,
                func.sum(UserUsageMetric.total_tokens).label("total_tokens"),
                func.sum(UserUsageMetric.total_input_tokens).label("input_tokens"),
                func.sum(UserUsageMetric.total_output_tokens).label("output_tokens"),
                func.sum(UserUsageMetric.total_cost_usd).label("total_cost"),
                func.sum(UserUsageMetric.total_queries).label("query_count"),
            )
            .filter(
                and_(
                    UserUsageMetric.date >= start_date, UserUsageMetric.date <= end_date
                )
            )
            .group_by(UserUsageMetric.date)
            .order_by(UserUsageMetric.date)
            .all()
        )

        data = []
        for row in daily_metrics:
            total_tokens = AnalyticsService._safe_int(row.total_tokens)
            # Use actual input/output tokens if available
            input_tokens = AnalyticsService._safe_int(row.input_tokens)
            output_tokens = AnalyticsService._safe_int(row.output_tokens)

            # Fallback to estimation if not tracked separately
            if input_tokens == 0 and output_tokens == 0 and total_tokens > 0:
                input_tokens = int(total_tokens * 0.8)
                output_tokens = total_tokens - input_tokens

            data.append(
                DailyTokenUsage(
                    date=row.date,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    cost_usd=round(AnalyticsService._safe_float(row.total_cost), 4),
                    query_count=AnalyticsService._safe_int(row.query_count),
                )
            )

        return DailyTokenUsageResponse(
            data=data, total_days=len(data), start_date=start_date, end_date=end_date
        )

    @staticmethod
    def get_top_users_by_cost(
        db: Session,
        limit: int = 10,
        period: TimePeriod = TimePeriod.MONTH,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> CostPerUserResponse:
        """
        Get top users by cost consumption.

        Aggregates from UserUsageMetric table.
        """
        start, end, period_label = AnalyticsService._get_date_range(
            period, start_date, end_date
        )

        # Aggregate user metrics
        user_costs = (
            db.query(
                UserUsageMetric.user_id,
                func.sum(UserUsageMetric.total_cost_usd).label("total_cost"),
                func.sum(UserUsageMetric.total_tokens).label("total_tokens"),
                func.sum(UserUsageMetric.total_queries).label("total_queries"),
                func.sum(UserUsageMetric.total_messages).label("total_messages"),
            )
            .filter(and_(UserUsageMetric.date >= start, UserUsageMetric.date <= end))
            .group_by(UserUsageMetric.user_id)
            .order_by(desc("total_cost"))
            .limit(limit)
            .all()
        )

        # Get user details
        top_users = []
        for rank, row in enumerate(user_costs, 1):
            user = db.query(User).filter(User.id == row.user_id).first()
            if user:
                top_users.append(
                    UserCostInfo(
                        user_id=row.user_id,
                        email=user.email,
                        full_name=user.full_name,
                        total_cost_usd=round(
                            AnalyticsService._safe_float(row.total_cost), 4
                        ),
                        total_tokens=AnalyticsService._safe_int(row.total_tokens),
                        total_queries=AnalyticsService._safe_int(row.total_queries),
                        total_messages=AnalyticsService._safe_int(row.total_messages),
                        rank=rank,
                    )
                )

        # Get totals
        total_users = (
            db.query(func.count(distinct(UserUsageMetric.user_id)))
            .filter(and_(UserUsageMetric.date >= start, UserUsageMetric.date <= end))
            .scalar()
            or 0
        )

        total_cost_all = (
            db.query(func.sum(UserUsageMetric.total_cost_usd))
            .filter(and_(UserUsageMetric.date >= start, UserUsageMetric.date <= end))
            .scalar()
        )

        return CostPerUserResponse(
            top_users=top_users,
            total_users=total_users,
            total_cost_all_users=round(AnalyticsService._safe_float(total_cost_all), 4),
            period=period_label,
        )

    # =========================================================================
    # 2. KNOWLEDGE BASE HEALTH
    # =========================================================================

    @staticmethod
    def get_knowledge_base_health(db: Session) -> KnowledgeBaseHealthResponse:
        """
        Get knowledge base health metrics.

        Data sources:
        - Document table: status, category, type
        - DocumentChunk table: chunk count
        """
        # Total documents
        total_docs = db.query(func.count(Document.id)).scalar() or 0

        # Active documents
        active_docs = (
            db.query(func.count(Document.id))
            .filter(Document.status == "active")
            .scalar()
            or 0
        )

        # Documents by category
        category_counts = (
            db.query(Document.category, func.count(Document.id).label("count"))
            .group_by(Document.category)
            .all()
        )

        categories = []
        for cat, count in category_counts:
            percentage = (count / total_docs * 100) if total_docs > 0 else 0
            categories.append(
                CategoryDistribution(
                    category=cat or "Unknown",
                    count=count,
                    percentage=round(percentage, 2),
                )
            )

        # Sort by count descending
        categories.sort(key=lambda x: x.count, reverse=True)

        # Documents by type
        type_counts = (
            db.query(Document.document_type, func.count(Document.id))
            .group_by(Document.document_type)
            .all()
        )
        docs_by_type = {t or "unknown": c for t, c in type_counts}

        # Documents by status
        status_counts = (
            db.query(Document.status, func.count(Document.id))
            .group_by(Document.status)
            .all()
        )
        docs_by_status = {s or "unknown": c for s, c in status_counts}

        # Total chunks
        total_chunks = db.query(func.count(DocumentChunk.id)).scalar() or 0

        # Average chunks per document
        avg_chunks = total_chunks / total_docs if total_docs > 0 else 0

        # Get documents with issues (not active)
        issue_docs = (
            db.query(Document)
            .filter(Document.status != "active")
            .order_by(desc(Document.created_at))
            .limit(20)
            .all()
        )

        upload_issues = [
            DocumentIssue(
                document_id=doc.document_id,
                document_uuid=doc.id,
                filename=doc.filename,
                document_name=doc.document_name,
                status=doc.status or "unknown",
                category=doc.category,
                created_at=doc.created_at,
            )
            for doc in issue_docs
        ]

        # Last upload time
        last_upload = db.query(func.max(Document.created_at)).scalar()

        return KnowledgeBaseHealthResponse(
            total_documents=total_docs,
            total_active_documents=active_docs,
            documents_by_category=categories,
            documents_by_type=docs_by_type,
            documents_by_status=docs_by_status,
            total_chunks=total_chunks,
            average_chunks_per_document=round(avg_chunks, 2),
            upload_issues=upload_issues,
            last_upload_at=last_upload,
        )

    # =========================================================================
    # 3. RAG PERFORMANCE
    # =========================================================================

    @staticmethod
    def get_rag_performance(
        db: Session,
        period: TimePeriod = TimePeriod.MONTH,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> RAGPerformanceResponse:
        """
        Get RAG system performance metrics.

        Data sources:
        - Query table: latency, rag_mode, retrieval_count
        - Message table: rag_mode, processing_time_ms
        """
        start, end, _ = AnalyticsService._get_date_range(period, start_date, end_date)
        start_dt = datetime.combine(start, datetime.min.time())
        end_dt = datetime.combine(end, datetime.max.time())

        # Base query filter
        base_filter = and_(Query.created_at >= start_dt, Query.created_at <= end_dt)

        # Average latency
        avg_latency = (
            db.query(func.avg(Query.total_latency_ms)).filter(base_filter).scalar()
        )

        # Latency percentiles using PERCENTILE_CONT
        percentile_query = (
            db.query(
                func.percentile_cont(0.5)
                .within_group(Query.total_latency_ms)
                .label("p50"),
                func.percentile_cont(0.75)
                .within_group(Query.total_latency_ms)
                .label("p75"),
                func.percentile_cont(0.9)
                .within_group(Query.total_latency_ms)
                .label("p90"),
                func.percentile_cont(0.95)
                .within_group(Query.total_latency_ms)
                .label("p95"),
                func.percentile_cont(0.99)
                .within_group(Query.total_latency_ms)
                .label("p99"),
            )
            .filter(base_filter)
            .first()
        )

        percentiles = LatencyPercentiles(
            p50=(
                AnalyticsService._safe_float(percentile_query.p50)
                if percentile_query
                else 0
            ),
            p75=(
                AnalyticsService._safe_float(percentile_query.p75)
                if percentile_query
                else 0
            ),
            p90=(
                AnalyticsService._safe_float(percentile_query.p90)
                if percentile_query
                else 0
            ),
            p95=(
                AnalyticsService._safe_float(percentile_query.p95)
                if percentile_query
                else 0
            ),
            p99=(
                AnalyticsService._safe_float(percentile_query.p99)
                if percentile_query
                else 0
            ),
        )

        # RAG mode distribution
        mode_counts = (
            db.query(Query.rag_mode, func.count(Query.id).label("count"))
            .filter(base_filter)
            .group_by(Query.rag_mode)
            .all()
        )

        total_queries = sum(c for _, c in mode_counts)
        mode_distribution = []
        for mode, count in mode_counts:
            percentage = (count / total_queries * 100) if total_queries > 0 else 0
            mode_distribution.append(
                RAGModeDistribution(
                    mode=mode or "unknown", count=count, percentage=round(percentage, 2)
                )
            )

        # Sort by count descending
        mode_distribution.sort(key=lambda x: x.count, reverse=True)

        # Average retrieval count
        avg_retrieval = (
            db.query(func.avg(Query.retrieval_count))
            .filter(and_(base_filter, Query.retrieval_count.isnot(None)))
            .scalar()
        )

        # Queries with retrieval
        queries_with_retrieval = (
            db.query(func.count(Query.id))
            .filter(and_(base_filter, Query.retrieval_count > 0))
            .scalar()
            or 0
        )

        # Latency by mode
        latency_by_mode_query = (
            db.query(
                Query.rag_mode, func.avg(Query.total_latency_ms).label("avg_latency")
            )
            .filter(base_filter)
            .group_by(Query.rag_mode)
            .all()
        )

        latency_by_mode = {
            mode or "unknown": round(AnalyticsService._safe_float(lat), 2)
            for mode, lat in latency_by_mode_query
        }

        return RAGPerformanceResponse(
            average_latency_ms=round(AnalyticsService._safe_float(avg_latency), 2),
            latency_percentiles=percentiles,
            rag_mode_distribution=mode_distribution,
            average_retrieval_count=round(
                AnalyticsService._safe_float(avg_retrieval), 2
            ),
            total_queries_analyzed=total_queries,
            queries_with_retrieval=queries_with_retrieval,
            latency_by_mode=latency_by_mode,
        )

    # =========================================================================
    # 4. QUALITY & FEEDBACK
    # =========================================================================

    @staticmethod
    def get_quality_feedback(
        db: Session,
        period: TimePeriod = TimePeriod.MONTH,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        recent_limit: int = 10,
    ) -> QualityFeedbackResponse:
        """
        Get quality and feedback metrics.

        Data sources:
        - Feedback table: rating, comment
        - Citation table: message citations
        - Message table: assistant messages count
        """
        start, end, _ = AnalyticsService._get_date_range(period, start_date, end_date)
        start_dt = datetime.combine(start, datetime.min.time())
        end_dt = datetime.combine(end, datetime.max.time())

        feedback_filter = and_(
            Feedback.created_at >= start_dt, Feedback.created_at <= end_dt
        )

        # CSAT score (average rating)
        csat = (
            db.query(func.avg(Feedback.rating))
            .filter(and_(feedback_filter, Feedback.rating.isnot(None)))
            .scalar()
        )

        # Total feedbacks
        total_feedbacks = (
            db.query(func.count(Feedback.id)).filter(feedback_filter).scalar() or 0
        )

        # Positive feedbacks (rating >= 4 or rating == 1 for thumbs up)
        positive = (
            db.query(func.count(Feedback.id))
            .filter(
                and_(
                    feedback_filter,
                    or_(Feedback.rating >= 4, Feedback.rating == 1),  # thumbs up
                )
            )
            .scalar()
            or 0
        )

        # Negative feedbacks (rating <= 2 or rating == -1 for thumbs down)
        negative = (
            db.query(func.count(Feedback.id))
            .filter(
                and_(
                    feedback_filter,
                    or_(
                        and_(Feedback.rating <= 2, Feedback.rating > 0),  # 1-2 rating
                        Feedback.rating == -1,  # thumbs down
                    ),
                )
            )
            .scalar()
            or 0
        )

        negative_rate = negative / total_feedbacks if total_feedbacks > 0 else 0

        # Rating distribution
        rating_counts = (
            db.query(Feedback.rating, func.count(Feedback.id).label("count"))
            .filter(feedback_filter)
            .group_by(Feedback.rating)
            .all()
        )

        rating_dist = []
        for rating, count in rating_counts:
            if rating is not None:
                percentage = (
                    (count / total_feedbacks * 100) if total_feedbacks > 0 else 0
                )
                rating_dist.append(
                    RatingDistribution(
                        rating=rating, count=count, percentage=round(percentage, 2)
                    )
                )
        rating_dist.sort(key=lambda x: x.rating, reverse=True)

        # Citation analysis
        message_filter = and_(
            Message.created_at >= start_dt,
            Message.created_at <= end_dt,
            Message.role == "assistant",
        )

        total_assistant_msgs = (
            db.query(func.count(Message.id)).filter(message_filter).scalar() or 0
        )

        # Messages with citations (subquery)
        msgs_with_citations = (
            db.query(func.count(distinct(Citation.message_id)))
            .filter(
                Citation.message_id.in_(db.query(Message.id).filter(message_filter))
            )
            .scalar()
            or 0
        )

        zero_citation = total_assistant_msgs - msgs_with_citations
        zero_citation_rate = (
            zero_citation / total_assistant_msgs if total_assistant_msgs > 0 else 0
        )

        # Recent comments
        recent_feedback_query = (
            db.query(Feedback)
            .filter(and_(feedback_filter, Feedback.comment.isnot(None)))
            .order_by(desc(Feedback.created_at))
            .limit(recent_limit)
            .all()
        )

        recent_comments = []
        for fb in recent_feedback_query:
            user = db.query(User).filter(User.id == fb.user_id).first()
            recent_comments.append(
                RecentFeedback(
                    feedback_id=fb.id,
                    user_email=user.email if user else None,
                    message_id=fb.message_id,
                    rating=fb.rating,
                    feedback_type=fb.feedback_type,
                    comment=fb.comment,
                    created_at=fb.created_at,
                )
            )

        return QualityFeedbackResponse(
            csat_score=round(AnalyticsService._safe_float(csat), 2) if csat else None,
            total_feedbacks=total_feedbacks,
            positive_feedbacks=positive,
            negative_feedbacks=negative,
            negative_feedback_rate=round(negative_rate, 4),
            rating_distribution=rating_dist,
            total_assistant_messages=total_assistant_msgs,
            messages_with_citations=msgs_with_citations,
            zero_citation_count=zero_citation,
            zero_citation_rate=round(zero_citation_rate, 4),
            recent_comments=recent_comments,
        )

    # =========================================================================
    # 5. USER ENGAGEMENT
    # =========================================================================

    @staticmethod
    def get_user_engagement(
        db: Session, top_queries_limit: int = 20, trend_days: int = 30
    ) -> UserEngagementResponse:
        """
        Get user engagement metrics.

        Data sources:
        - User table: registered users
        - UserUsageMetric table: daily active users
        - Query table: popular queries
        """
        today = date.today()

        # DAU - Users with activity today
        dau = (
            db.query(func.count(distinct(UserUsageMetric.user_id)))
            .filter(UserUsageMetric.date == today)
            .scalar()
            or 0
        )

        # WAU - Users with activity in last 7 days
        week_ago = today - timedelta(days=7)
        wau = (
            db.query(func.count(distinct(UserUsageMetric.user_id)))
            .filter(UserUsageMetric.date >= week_ago)
            .scalar()
            or 0
        )

        # MAU - Users with activity in last 30 days
        month_ago = today - timedelta(days=30)
        mau = (
            db.query(func.count(distinct(UserUsageMetric.user_id)))
            .filter(UserUsageMetric.date >= month_ago)
            .scalar()
            or 0
        )

        # Total registered users
        total_users = (
            db.query(func.count(User.id)).filter(User.deleted_at.is_(None)).scalar()
            or 0
        )

        # DAU/MAU ratio
        dau_mau_ratio = dau / mau if mau > 0 else 0

        # Average queries per user (last 30 days)
        total_queries_30d = (
            db.query(func.sum(UserUsageMetric.total_queries))
            .filter(UserUsageMetric.date >= month_ago)
            .scalar()
            or 0
        )
        avg_queries_per_user = total_queries_30d / mau if mau > 0 else 0

        # Average conversations per user
        conv_count = (
            db.query(func.count(Conversation.id))
            .filter(
                Conversation.created_at
                >= datetime.combine(month_ago, datetime.min.time())
            )
            .scalar()
            or 0
        )
        avg_conv_per_user = conv_count / mau if mau > 0 else 0

        # Top queries (using query_hash to group similar queries)
        top_queries_result = (
            db.query(
                Query.query_text,
                func.count(Query.id).label("count"),
                func.count(distinct(Query.user_id)).label("unique_users"),
            )
            .filter(
                Query.created_at >= datetime.combine(month_ago, datetime.min.time())
            )
            .group_by(Query.query_hash, Query.query_text)
            .order_by(desc("count"))
            .limit(top_queries_limit)
            .all()
        )

        top_queries = [
            TopQuery(
                query_text=(
                    q.query_text[:100] + "..."
                    if len(q.query_text) > 100
                    else q.query_text
                ),
                count=q.count,
                unique_users=q.unique_users,
            )
            for q in top_queries_result
        ]

        # Engagement trend (last N days)
        trend_start = today - timedelta(days=trend_days)
        daily_engagement = (
            db.query(
                UserUsageMetric.date,
                func.count(distinct(UserUsageMetric.user_id)).label("active_users"),
                func.sum(UserUsageMetric.total_queries).label("total_queries"),
            )
            .filter(UserUsageMetric.date >= trend_start)
            .group_by(UserUsageMetric.date)
            .order_by(UserUsageMetric.date)
            .all()
        )

        engagement_trend = [
            EngagementTrend(
                date=row.date,
                active_users=row.active_users,
                total_queries=AnalyticsService._safe_int(row.total_queries),
                total_conversations=0,  # Would need separate query
            )
            for row in daily_engagement
        ]

        return UserEngagementResponse(
            dau=dau,
            wau=wau,
            mau=mau,
            total_registered_users=total_users,
            dau_mau_ratio=round(dau_mau_ratio, 4),
            avg_queries_per_user=round(avg_queries_per_user, 2),
            avg_conversations_per_user=round(avg_conv_per_user, 2),
            top_queries=top_queries,
            engagement_trend=engagement_trend,
        )

    # =========================================================================
    # 6. DASHBOARD SUMMARY
    # =========================================================================

    @staticmethod
    def get_dashboard_summary(
        db: Session,
        period: TimePeriod = TimePeriod.MONTH,
        include_details: bool = False,
    ) -> DashboardSummaryResponse:
        """
        Get combined dashboard summary with all metrics.

        Args:
            db: Database session
            period: Time period for aggregation
            include_details: If True, include full detail sections
        """
        start, end, period_label = AnalyticsService._get_date_range(period)

        # Get individual metrics
        cost = AnalyticsService.get_cost_overview(db, period)
        kb_health = AnalyticsService.get_knowledge_base_health(db)
        rag_perf = AnalyticsService.get_rag_performance(db, period)
        feedback = AnalyticsService.get_quality_feedback(db, period)
        engagement = AnalyticsService.get_user_engagement(db)

        # Build key metrics
        key_metrics = {
            "total_cost_usd": cost.total_cost_usd,
            "total_queries": cost.total_queries,
            "average_cost_per_query": cost.average_cost_per_query,
            "total_documents": kb_health.total_active_documents,
            "total_chunks": kb_health.total_chunks,
            "avg_latency_ms": rag_perf.average_latency_ms,
            "csat_score": feedback.csat_score,
            "zero_citation_rate": feedback.zero_citation_rate,
            "dau": engagement.dau,
            "mau": engagement.mau,
        }

        return DashboardSummaryResponse(
            generated_at=datetime.utcnow(),
            period=period_label,
            key_metrics=key_metrics,
            cost_overview=cost if include_details else None,
            knowledge_base=kb_health if include_details else None,
            rag_performance=rag_perf if include_details else None,
            quality_feedback=feedback if include_details else None,
            user_engagement=engagement if include_details else None,
        )


# Singleton instance
analytics_service = AnalyticsService()
