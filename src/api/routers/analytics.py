"""
Analytics Router - Dashboard API Endpoints
Provides endpoints for analytics and dashboard data
"""

import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.models.base import get_db
from src.models.users import User
from src.auth.dependencies import get_current_active_user, require_role

from src.api.schemas.analytics_schemas import (
    TimePeriod,
    CostOverviewResponse,
    DailyTokenUsageResponse,
    CostPerUserResponse,
    KnowledgeBaseHealthResponse,
    RAGPerformanceResponse,
    QualityFeedbackResponse,
    UserEngagementResponse,
    DashboardSummaryResponse,
)
from src.api.services.analytics_service import analytics_service
from src.api.services.analytics_cache import (
    get_analytics_cache,
    CacheKeyPrefix,
    CacheTTL,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# =============================================================================
# DASHBOARD SUMMARY
# =============================================================================


@router.get("/overview", response_model=DashboardSummaryResponse)
async def get_dashboard_overview(
    period: TimePeriod = Query(
        TimePeriod.MONTH, description="Time period for aggregation"
    ),
    include_details: bool = Query(False, description="Include full detail sections"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get dashboard overview with all key metrics.

    Returns a summary of all analytics data:
    - Cost overview
    - Knowledge base health
    - RAG performance
    - Quality & feedback
    - User engagement

    Set `include_details=true` to get full data for each section.
    """
    try:
        return analytics_service.get_dashboard_summary(
            db=db, period=period, include_details=include_details
        )
    except Exception as e:
        logger.error(f"Error getting dashboard overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard overview: {str(e)}",
        )


# =============================================================================
# COST ANALYTICS
# =============================================================================


@router.get("/cost", response_model=CostOverviewResponse)
async def get_cost_overview(
    period: TimePeriod = Query(
        TimePeriod.MONTH, description="Time period for aggregation"
    ),
    start_date: Optional[date] = Query(
        None, description="Custom start date (overrides period)"
    ),
    end_date: Optional[date] = Query(
        None, description="Custom end date (overrides period)"
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get cost overview metrics.

    Returns:
    - Total cost in USD
    - Token breakdown (input/output)
    - Average cost per query
    - Total queries and conversations
    """
    try:
        return analytics_service.get_cost_overview(
            db=db, period=period, start_date=start_date, end_date=end_date
        )
    except Exception as e:
        logger.error(f"Error getting cost overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cost overview: {str(e)}",
        )


@router.get("/cost/daily", response_model=DailyTokenUsageResponse)
async def get_daily_token_usage(
    start_date: date = Query(
        default_factory=lambda: date.today() - timedelta(days=30),
        description="Start date for the range",
    ),
    end_date: date = Query(
        default_factory=date.today, description="End date for the range"
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get daily token usage for chart visualization.

    Returns daily breakdown of:
    - Input tokens
    - Output tokens
    - Total cost
    - Query count

    Useful for line charts showing usage trends over time.
    """
    # Validate date range
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date",
        )

    max_days = 365
    if (end_date - start_date).days > max_days:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Date range cannot exceed {max_days} days",
        )

    try:
        return analytics_service.get_daily_token_usage(
            db=db, start_date=start_date, end_date=end_date
        )
    except Exception as e:
        logger.error(f"Error getting daily token usage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get daily token usage: {str(e)}",
        )


@router.get("/cost/users", response_model=CostPerUserResponse)
async def get_cost_per_user(
    limit: int = Query(10, ge=1, le=100, description="Number of top users to return"),
    period: TimePeriod = Query(
        TimePeriod.MONTH, description="Time period for aggregation"
    ),
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    """
    Get top users by cost consumption.

    Returns ranked list of users with highest cost consumption.
    Useful for identifying heavy users and optimizing resource allocation.

    **Admin only** - exposes user email addresses and cost data.

    Requires: admin role
    """
    try:
        return analytics_service.get_top_users_by_cost(
            db=db, limit=limit, period=period
        )
    except Exception as e:
        logger.error(f"Error getting cost per user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cost per user: {str(e)}",
        )


# =============================================================================
# KNOWLEDGE BASE HEALTH
# =============================================================================


@router.get("/knowledge-base", response_model=KnowledgeBaseHealthResponse)
async def get_knowledge_base_health(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get knowledge base health metrics.

    Returns:
    - Total and active documents count
    - Documents distribution by category and type
    - Total chunks count
    - Documents with issues (not active status)
    - Last upload timestamp

    Useful for monitoring data quality and identifying gaps.
    """
    try:
        return analytics_service.get_knowledge_base_health(db=db)
    except Exception as e:
        logger.error(f"Error getting knowledge base health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get knowledge base health: {str(e)}",
        )


# =============================================================================
# RAG PERFORMANCE
# =============================================================================


@router.get("/performance", response_model=RAGPerformanceResponse)
async def get_rag_performance(
    period: TimePeriod = Query(
        TimePeriod.MONTH, description="Time period for aggregation"
    ),
    start_date: Optional[date] = Query(None, description="Custom start date"),
    end_date: Optional[date] = Query(None, description="Custom end date"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get RAG system performance metrics.

    Returns:
    - Average latency and percentiles (p50, p75, p90, p95, p99)
    - RAG mode distribution
    - Average retrieval count
    - Latency breakdown by RAG mode

    Useful for monitoring system performance and identifying bottlenecks.
    """
    try:
        return analytics_service.get_rag_performance(
            db=db, period=period, start_date=start_date, end_date=end_date
        )
    except Exception as e:
        logger.error(f"Error getting RAG performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get RAG performance: {str(e)}",
        )


# =============================================================================
# QUALITY & FEEDBACK
# =============================================================================


@router.get("/feedback", response_model=QualityFeedbackResponse)
async def get_quality_feedback(
    period: TimePeriod = Query(
        TimePeriod.MONTH, description="Time period for aggregation"
    ),
    recent_limit: int = Query(
        10, ge=1, le=50, description="Number of recent comments to return"
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get quality and feedback metrics.

    Returns:
    - CSAT score (average rating)
    - Positive/negative feedback rates
    - Rating distribution
    - Zero-citation rate (potential hallucination indicator)
    - Recent feedback comments

    Useful for monitoring user satisfaction and identifying quality issues.
    """
    try:
        return analytics_service.get_quality_feedback(
            db=db, period=period, recent_limit=recent_limit
        )
    except Exception as e:
        logger.error(f"Error getting quality feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get quality feedback: {str(e)}",
        )


# =============================================================================
# USER ENGAGEMENT
# =============================================================================


@router.get("/engagement", response_model=UserEngagementResponse)
async def get_user_engagement(
    top_queries_limit: int = Query(
        20, ge=1, le=100, description="Number of top queries to return"
    ),
    trend_days: int = Query(
        30, ge=7, le=90, description="Number of days for trend data"
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get user engagement metrics.

    Returns:
    - DAU/WAU/MAU (Daily/Weekly/Monthly Active Users)
    - DAU/MAU ratio (stickiness)
    - Average queries per user
    - Top searched queries
    - Daily engagement trend

    Useful for understanding user behavior and identifying popular topics.
    """
    try:
        return analytics_service.get_user_engagement(
            db=db, top_queries_limit=top_queries_limit, trend_days=trend_days
        )
    except Exception as e:
        logger.error(f"Error getting user engagement: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user engagement: {str(e)}",
        )


# =============================================================================
# ADMIN - METRICS AGGREGATION
# =============================================================================

from src.api.services.metrics_aggregator import metrics_aggregator
from pydantic import BaseModel
from typing import List


class AggregationRequest(BaseModel):
    """Request for metrics aggregation"""

    target_date: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class AggregationResponse(BaseModel):
    """Response from metrics aggregation"""

    success: bool
    message: str
    details: dict


class CacheStatsResponse(BaseModel):
    """Cache statistics response"""

    enabled: bool
    hits: int
    misses: int
    errors: int
    total: int
    hit_rate: float


@router.post("/admin/aggregate", response_model=AggregationResponse)
async def trigger_metrics_aggregation(
    request: AggregationRequest,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    """
    Trigger metrics aggregation for a specific date or date range.

    **Admin only** - triggers background aggregation of usage metrics.

    - If `target_date` is provided: aggregates for that single date
    - If `start_date` and `end_date` are provided: backfills range
    - If nothing provided: aggregates for yesterday

    Requires: admin role
    """
    try:
        if request.start_date and request.end_date:
            # Backfill date range
            result = metrics_aggregator.backfill_historical_metrics(
                db=db, start_date=request.start_date, end_date=request.end_date
            )
            return AggregationResponse(
                success=True,
                message=f"Backfilled metrics for {result['days_processed']} days",
                details=result,
            )

        # Single date aggregation
        target = request.target_date or (date.today() - timedelta(days=1))
        result = metrics_aggregator.aggregate_all_users_daily(db=db, target_date=target)

        return AggregationResponse(
            success=True, message=f"Aggregated metrics for {target}", details=result
        )

    except Exception as e:
        logger.error(f"Error aggregating metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to aggregate metrics: {str(e)}",
        )


@router.get("/admin/aggregation-status")
async def get_aggregation_status(
    days: int = Query(30, ge=1, le=365, description="Number of days to check"),
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    """
    Get status of metrics aggregation for recent days.

    Shows which days have been aggregated and any gaps.

    **Admin only**

    Requires: admin role
    """
    try:
        return metrics_aggregator.get_aggregation_status(db=db, days=days)
    except Exception as e:
        logger.error(f"Error getting aggregation status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get aggregation status: {str(e)}",
        )


@router.post("/admin/recalculate-tokens")
async def recalculate_token_split(
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    """
    Recalculate input/output token split for records missing this data.

    Uses 80/20 estimation for queries and metrics where separate
    input/output tokens weren't tracked.

    **Admin only**

    Requires: admin role
    """
    try:
        result = metrics_aggregator.recalculate_token_split(db=db)
        return {"success": True, "message": "Token split recalculated", **result}
    except Exception as e:
        logger.error(f"Error recalculating token split: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to recalculate token split: {str(e)}",
        )


@router.get("/admin/cache-stats", response_model=CacheStatsResponse)
async def get_cache_stats(
    current_user: User = Depends(require_role(["admin"])),
):
    """
    Get analytics cache statistics.

    Shows cache hit rate and error counts.

    **Admin only**

    Requires: admin role
    """
    cache = get_analytics_cache()
    stats = cache.stats
    return CacheStatsResponse(enabled=cache.is_enabled, **stats)


@router.post("/admin/invalidate-cache")
async def invalidate_cache(
    cache_type: Optional[str] = Query(
        None, description="Cache type to invalidate: 'cost', 'kb', or None for all"
    ),
    current_user: User = Depends(require_role(["admin"])),
):
    """
    Invalidate analytics cache.

    - `cost`: Invalidate cost-related caches
    - `kb`: Invalidate knowledge base caches
    - None/empty: Invalidate all analytics caches

    **Admin only**

    Requires: admin role
    """
    cache = get_analytics_cache()

    if not cache.is_enabled:
        return {"success": True, "message": "Caching is not enabled"}

    if cache_type == "cost":
        cache.invalidate_cost_cache()
        return {"success": True, "message": "Cost cache invalidated"}
    elif cache_type == "kb":
        cache.invalidate_kb_cache()
        return {"success": True, "message": "Knowledge base cache invalidated"}
    else:
        cache.invalidate_all()
        return {"success": True, "message": "All analytics caches invalidated"}
