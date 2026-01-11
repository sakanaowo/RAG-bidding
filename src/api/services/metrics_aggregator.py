"""
Usage Metrics Aggregation Service
Aggregates data from Query, Message, Conversation tables into UserUsageMetric
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, distinct, text

from src.models.users import User
from src.models.conversations import Conversation
from src.models.messages import Message
from src.models.queries import Query
from src.models.user_metrics import UserUsageMetric

logger = logging.getLogger(__name__)


class UsageMetricsAggregator:
    """
    Service for aggregating usage metrics from source tables.

    Aggregates data from:
    - Query: tokens, cost, latency, categories
    - Message: message count
    - Conversation: conversation count

    Into:
    - UserUsageMetric: daily aggregated metrics per user
    """

    # Cost per token (in USD) for GPT-4o-mini
    # Input: $0.15 per 1M tokens
    # Output: $0.60 per 1M tokens
    INPUT_TOKEN_COST = 0.00000015
    OUTPUT_TOKEN_COST = 0.0000006

    @staticmethod
    def aggregate_user_daily_metrics(
        db: Session, user_id: UUID, target_date: date, create_if_missing: bool = True
    ) -> Optional[UserUsageMetric]:
        """
        Aggregate metrics for a specific user and date.

        Args:
            db: Database session
            user_id: User UUID
            target_date: Date to aggregate for
            create_if_missing: Create new metric if not exists

        Returns:
            Updated or created UserUsageMetric
        """
        # Convert date to datetime range
        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = datetime.combine(target_date, datetime.max.time())

        # Query aggregation from Query table
        query_stats = (
            db.query(
                func.count(Query.id).label("query_count"),
                func.coalesce(func.sum(Query.tokens_total), 0).label("total_tokens"),
                func.coalesce(func.sum(Query.input_tokens), 0).label("input_tokens"),
                func.coalesce(func.sum(Query.output_tokens), 0).label("output_tokens"),
                func.coalesce(func.sum(Query.estimated_cost_usd), 0).label(
                    "total_cost"
                ),
            )
            .filter(
                and_(
                    Query.user_id == user_id,
                    Query.created_at >= start_dt,
                    Query.created_at <= end_dt,
                )
            )
            .first()
        )

        # Get categories accessed
        categories_result = (
            db.query(func.unnest(Query.categories_searched).label("category"))
            .filter(
                and_(
                    Query.user_id == user_id,
                    Query.created_at >= start_dt,
                    Query.created_at <= end_dt,
                    Query.categories_searched.isnot(None),
                )
            )
            .distinct()
            .all()
        )

        categories_accessed = list(
            set(c.category for c in categories_result if c.category)
        )

        # Message count
        message_count = (
            db.query(func.count(Message.id))
            .join(Conversation, Message.conversation_id == Conversation.id)
            .filter(
                and_(
                    Conversation.user_id == user_id,
                    Message.created_at >= start_dt,
                    Message.created_at <= end_dt,
                    Message.role == "user",  # Only count user messages
                )
            )
            .scalar()
            or 0
        )

        # Get or create metric
        metric = (
            db.query(UserUsageMetric)
            .filter(
                and_(
                    UserUsageMetric.user_id == user_id,
                    UserUsageMetric.date == target_date,
                )
            )
            .first()
        )

        if metric is None:
            if not create_if_missing:
                return None
            metric = UserUsageMetric(user_id=user_id, date=target_date)
            db.add(metric)

        # Extract token values
        total_tokens = int(query_stats.total_tokens) if query_stats.total_tokens else 0
        input_tokens = int(query_stats.input_tokens) if query_stats.input_tokens else 0
        output_tokens = (
            int(query_stats.output_tokens) if query_stats.output_tokens else 0
        )

        # If input/output not tracked separately, estimate
        if input_tokens == 0 and output_tokens == 0 and total_tokens > 0:
            input_tokens = int(total_tokens * 0.8)
            output_tokens = total_tokens - input_tokens

        # Calculate cost if not already calculated
        total_cost = float(query_stats.total_cost) if query_stats.total_cost else 0
        if total_cost == 0 and total_tokens > 0:
            total_cost = (
                input_tokens * UsageMetricsAggregator.INPUT_TOKEN_COST
                + output_tokens * UsageMetricsAggregator.OUTPUT_TOKEN_COST
            )

        # Update metric
        metric.total_queries = (
            int(query_stats.query_count) if query_stats.query_count else 0
        )
        metric.total_messages = message_count
        metric.total_tokens = total_tokens
        metric.total_input_tokens = input_tokens
        metric.total_output_tokens = output_tokens
        metric.total_cost_usd = Decimal(str(round(total_cost, 4)))
        metric.categories_accessed = (
            categories_accessed if categories_accessed else None
        )

        return metric

    @staticmethod
    def aggregate_all_users_daily(
        db: Session, target_date: date, batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        Aggregate metrics for all active users for a specific date.

        Args:
            db: Database session
            target_date: Date to aggregate
            batch_size: Number of users to process at once

        Returns:
            Summary of aggregation results
        """
        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = datetime.combine(target_date, datetime.max.time())

        # Get all users with activity on target date
        active_users = (
            db.query(distinct(Query.user_id))
            .filter(
                and_(
                    Query.user_id.isnot(None),
                    Query.created_at >= start_dt,
                    Query.created_at <= end_dt,
                )
            )
            .all()
        )

        user_ids = [u[0] for u in active_users]

        results = {
            "date": target_date.isoformat(),
            "users_processed": 0,
            "users_skipped": 0,
            "errors": [],
            "total_queries": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
        }

        for user_id in user_ids:
            try:
                metric = UsageMetricsAggregator.aggregate_user_daily_metrics(
                    db=db, user_id=user_id, target_date=target_date
                )

                if metric:
                    results["users_processed"] += 1
                    results["total_queries"] += metric.total_queries or 0
                    results["total_tokens"] += metric.total_tokens or 0
                    results["total_cost"] += float(metric.total_cost_usd or 0)
                else:
                    results["users_skipped"] += 1

            except Exception as e:
                results["errors"].append({"user_id": str(user_id), "error": str(e)})
                logger.error(f"Error aggregating metrics for user {user_id}: {e}")

        # Commit changes
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error committing aggregated metrics: {e}")
            raise

        results["total_cost"] = round(results["total_cost"], 4)

        logger.info(
            f"Aggregated metrics for {target_date}: "
            f"{results['users_processed']} users, "
            f"{results['total_queries']} queries, "
            f"${results['total_cost']}"
        )

        return results

    @staticmethod
    def backfill_historical_metrics(
        db: Session, start_date: date, end_date: date
    ) -> Dict[str, Any]:
        """
        Backfill historical metrics for a date range.

        Args:
            db: Database session
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Summary of backfill results
        """
        results = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days_processed": 0,
            "total_users": 0,
            "total_queries": 0,
            "total_cost": 0.0,
            "daily_results": [],
        }

        current_date = start_date
        while current_date <= end_date:
            try:
                daily_result = UsageMetricsAggregator.aggregate_all_users_daily(
                    db=db, target_date=current_date
                )

                results["days_processed"] += 1
                results["total_users"] += daily_result["users_processed"]
                results["total_queries"] += daily_result["total_queries"]
                results["total_cost"] += daily_result["total_cost"]
                results["daily_results"].append(daily_result)

            except Exception as e:
                logger.error(f"Error backfilling metrics for {current_date}: {e}")
                results["daily_results"].append(
                    {"date": current_date.isoformat(), "error": str(e)}
                )

            current_date += timedelta(days=1)

        results["total_cost"] = round(results["total_cost"], 4)

        return results

    @staticmethod
    def recalculate_token_split(db: Session) -> Dict[str, Any]:
        """
        Recalculate input/output token split for queries where it's missing.

        This updates queries and user metrics where input_tokens/output_tokens
        are NULL but tokens_total is available.

        Returns:
            Summary of updates made
        """
        # Update queries
        queries_updated = db.execute(
            text(
                """
            UPDATE queries 
            SET input_tokens = FLOOR(tokens_total * 0.8)::INTEGER,
                output_tokens = tokens_total - FLOOR(tokens_total * 0.8)::INTEGER
            WHERE tokens_total IS NOT NULL 
            AND (input_tokens IS NULL OR output_tokens IS NULL)
        """
            )
        ).rowcount

        # Update user metrics
        metrics_updated = db.execute(
            text(
                """
            UPDATE user_usage_metrics 
            SET total_input_tokens = FLOOR(total_tokens * 0.8)::BIGINT,
                total_output_tokens = total_tokens - FLOOR(total_tokens * 0.8)::BIGINT
            WHERE total_tokens IS NOT NULL 
            AND (total_input_tokens IS NULL OR total_output_tokens IS NULL)
        """
            )
        ).rowcount

        db.commit()

        return {"queries_updated": queries_updated, "metrics_updated": metrics_updated}

    @staticmethod
    def get_aggregation_status(db: Session, days: int = 30) -> Dict[str, Any]:
        """
        Get status of metric aggregation for recent days.

        Returns which days have been aggregated and any gaps.
        """
        today = date.today()
        start_date = today - timedelta(days=days)

        # Get dates with metrics
        aggregated_dates = (
            db.query(
                UserUsageMetric.date,
                func.count(distinct(UserUsageMetric.user_id)).label("user_count"),
                func.sum(UserUsageMetric.total_queries).label("total_queries"),
            )
            .filter(UserUsageMetric.date >= start_date)
            .group_by(UserUsageMetric.date)
            .all()
        )

        aggregated_dict = {
            row.date: {
                "user_count": row.user_count,
                "total_queries": row.total_queries or 0,
            }
            for row in aggregated_dates
        }

        # Check for gaps
        status = []
        current = start_date
        while current <= today:
            if current in aggregated_dict:
                status.append(
                    {
                        "date": current.isoformat(),
                        "status": "aggregated",
                        **aggregated_dict[current],
                    }
                )
            else:
                status.append(
                    {
                        "date": current.isoformat(),
                        "status": "missing",
                        "user_count": 0,
                        "total_queries": 0,
                    }
                )
            current += timedelta(days=1)

        missing_days = [s["date"] for s in status if s["status"] == "missing"]

        return {
            "period_start": start_date.isoformat(),
            "period_end": today.isoformat(),
            "total_days": days + 1,
            "aggregated_days": len(aggregated_dict),
            "missing_days": len(missing_days),
            "missing_dates": missing_days,
            "daily_status": status,
        }


# Singleton instance
metrics_aggregator = UsageMetricsAggregator()
