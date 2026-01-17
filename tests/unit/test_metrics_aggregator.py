"""
Unit Tests for Metrics Aggregator Service
Tests usage metrics aggregation functionality
"""

import pytest
from datetime import date, datetime, timedelta
from uuid import uuid4
from decimal import Decimal
from unittest.mock import MagicMock, patch, PropertyMock

from src.api.services.metrics_aggregator import (
    UsageMetricsAggregator,
    metrics_aggregator,
)


class TestUsageMetricsAggregatorConstants:
    """Tests for aggregator constants"""

    def test_input_token_cost(self):
        """Test input token cost constant"""
        assert UsageMetricsAggregator.INPUT_TOKEN_COST == 0.00000015

    def test_output_token_cost(self):
        """Test output token cost constant"""
        assert UsageMetricsAggregator.OUTPUT_TOKEN_COST == 0.0000006

    def test_singleton_instance(self):
        """Test singleton instance exists"""
        assert metrics_aggregator is not None
        assert isinstance(metrics_aggregator, UsageMetricsAggregator)


class TestAggregateUserDailyMetrics:
    """Tests for aggregate_user_daily_metrics method"""

    def test_aggregate_with_existing_data(self, mock_aggregator_db_session):
        """Test aggregation with existing query data"""
        user_id = uuid4()
        target_date = date.today()

        # Mock the metric query to return existing metric
        existing_metric = MagicMock()
        existing_metric.total_queries = 0

        mock_aggregator_db_session.query.return_value.filter.return_value.first.return_value = (
            existing_metric
        )

        result = UsageMetricsAggregator.aggregate_user_daily_metrics(
            db=mock_aggregator_db_session, user_id=user_id, target_date=target_date
        )

        # Should update the existing metric
        assert result == existing_metric

    def test_aggregate_creates_new_metric(self, mock_aggregator_db_session):
        """Test aggregation creates new metric when none exists"""
        user_id = uuid4()
        target_date = date.today()

        # First call for query stats returns data
        query_stats_mock = MagicMock()
        query_stats_mock.query_count = 5
        query_stats_mock.total_tokens = 2500
        query_stats_mock.input_tokens = 2000
        query_stats_mock.output_tokens = 500
        query_stats_mock.total_cost = Decimal("0.25")

        # Categories query returns empty
        categories_mock = MagicMock()
        categories_mock.all.return_value = []

        # Set up the mock chain
        query_mock = MagicMock()
        query_mock.filter.return_value = query_mock
        query_mock.first.side_effect = [
            query_stats_mock,
            None,
        ]  # Stats first, then no existing metric
        query_mock.distinct.return_value.all.return_value = []
        query_mock.scalar.return_value = 3

        mock_aggregator_db_session.query.return_value = query_mock

        with patch("src.api.services.metrics_aggregator.UserUsageMetric") as MockMetric:
            mock_metric = MagicMock()
            MockMetric.return_value = mock_metric

            result = UsageMetricsAggregator.aggregate_user_daily_metrics(
                db=mock_aggregator_db_session,
                user_id=user_id,
                target_date=target_date,
                create_if_missing=True,
            )

            # Should have added new metric
            mock_aggregator_db_session.add.assert_called()

    def test_aggregate_no_create_returns_none(self, mock_aggregator_db_session):
        """Test aggregation returns None when create_if_missing=False and no metric exists"""
        user_id = uuid4()
        target_date = date.today()

        # Mock query chain
        query_mock = MagicMock()
        query_mock.filter.return_value = query_mock
        query_mock.first.side_effect = [
            MagicMock(
                query_count=0,
                total_tokens=0,
                input_tokens=0,
                output_tokens=0,
                total_cost=0,
            ),
            None,  # No existing metric
        ]
        query_mock.distinct.return_value.all.return_value = []
        query_mock.scalar.return_value = 0

        mock_aggregator_db_session.query.return_value = query_mock

        result = UsageMetricsAggregator.aggregate_user_daily_metrics(
            db=mock_aggregator_db_session,
            user_id=user_id,
            target_date=target_date,
            create_if_missing=False,
        )

        assert result is None

    def test_aggregate_token_estimation_fallback(self, mock_aggregator_db_session):
        """Test that token split is estimated when not tracked separately"""
        user_id = uuid4()
        target_date = date.today()

        # Mock stats with only total_tokens (no input/output)
        query_stats_mock = MagicMock()
        query_stats_mock.query_count = 10
        query_stats_mock.total_tokens = 5000
        query_stats_mock.input_tokens = 0
        query_stats_mock.output_tokens = 0
        query_stats_mock.total_cost = Decimal("0")

        existing_metric = MagicMock()

        query_mock = MagicMock()
        query_mock.filter.return_value = query_mock
        query_mock.first.side_effect = [query_stats_mock, existing_metric]
        query_mock.distinct.return_value.all.return_value = []
        query_mock.scalar.return_value = 0

        mock_aggregator_db_session.query.return_value = query_mock

        result = UsageMetricsAggregator.aggregate_user_daily_metrics(
            db=mock_aggregator_db_session, user_id=user_id, target_date=target_date
        )

        # Should have estimated 80/20 split
        assert existing_metric.total_input_tokens == 4000  # 80% of 5000
        assert existing_metric.total_output_tokens == 1000  # 20% of 5000


class TestAggregateAllUsersDaily:
    """Tests for aggregate_all_users_daily method"""

    def test_aggregate_all_users(self, mock_aggregator_db_session):
        """Test aggregation for all active users"""
        target_date = date.today()

        # Mock active users query
        user1_id = uuid4()
        user2_id = uuid4()

        active_users_mock = MagicMock()
        active_users_mock.all.return_value = [(user1_id,), (user2_id,)]

        query_mock = MagicMock()
        query_mock.filter.return_value = active_users_mock
        mock_aggregator_db_session.query.return_value = query_mock

        with patch.object(
            UsageMetricsAggregator, "aggregate_user_daily_metrics"
        ) as mock_aggregate:
            mock_metric = MagicMock()
            mock_metric.total_queries = 5
            mock_metric.total_tokens = 2500
            mock_metric.total_cost_usd = Decimal("0.25")
            mock_aggregate.return_value = mock_metric

            result = UsageMetricsAggregator.aggregate_all_users_daily(
                db=mock_aggregator_db_session, target_date=target_date
            )

            assert result["date"] == target_date.isoformat()
            assert result["users_processed"] == 2
            assert mock_aggregate.call_count == 2

    def test_aggregate_handles_errors(self, mock_aggregator_db_session):
        """Test that errors for individual users are logged but don't stop processing"""
        target_date = date.today()

        user1_id = uuid4()
        user2_id = uuid4()

        active_users_mock = MagicMock()
        active_users_mock.all.return_value = [(user1_id,), (user2_id,)]

        query_mock = MagicMock()
        query_mock.filter.return_value = active_users_mock
        mock_aggregator_db_session.query.return_value = query_mock

        with patch.object(
            UsageMetricsAggregator, "aggregate_user_daily_metrics"
        ) as mock_aggregate:
            # First call succeeds, second fails
            mock_metric = MagicMock()
            mock_metric.total_queries = 5
            mock_metric.total_tokens = 2500
            mock_metric.total_cost_usd = Decimal("0.25")
            mock_aggregate.side_effect = [mock_metric, Exception("Test error")]

            result = UsageMetricsAggregator.aggregate_all_users_daily(
                db=mock_aggregator_db_session, target_date=target_date
            )

            assert result["users_processed"] == 1
            assert len(result["errors"]) == 1


class TestBackfillHistoricalMetrics:
    """Tests for backfill_historical_metrics method"""

    def test_backfill_date_range(self, mock_aggregator_db_session):
        """Test backfilling metrics for a date range"""
        start_date = date(2026, 1, 1)
        end_date = date(2026, 1, 3)

        with patch.object(
            UsageMetricsAggregator, "aggregate_all_users_daily"
        ) as mock_aggregate:
            mock_aggregate.return_value = {
                "date": "2026-01-01",
                "users_processed": 10,
                "total_queries": 100,
                "total_cost": 5.0,
            }

            result = UsageMetricsAggregator.backfill_historical_metrics(
                db=mock_aggregator_db_session, start_date=start_date, end_date=end_date
            )

            assert result["days_processed"] == 3
            assert mock_aggregate.call_count == 3

    def test_backfill_handles_errors(self, mock_aggregator_db_session):
        """Test backfill continues on individual day errors"""
        start_date = date(2026, 1, 1)
        end_date = date(2026, 1, 2)

        with patch.object(
            UsageMetricsAggregator, "aggregate_all_users_daily"
        ) as mock_aggregate:
            mock_aggregate.side_effect = [
                {
                    "date": "2026-01-01",
                    "users_processed": 10,
                    "total_queries": 100,
                    "total_cost": 5.0,
                },
                Exception("Test error"),
            ]

            result = UsageMetricsAggregator.backfill_historical_metrics(
                db=mock_aggregator_db_session, start_date=start_date, end_date=end_date
            )

            assert result["days_processed"] == 1
            assert len(result["daily_results"]) == 2


class TestRecalculateTokenSplit:
    """Tests for recalculate_token_split method"""

    def test_recalculate_tokens(self, mock_aggregator_db_session):
        """Test recalculating token split for records"""
        mock_aggregator_db_session.execute.return_value = MagicMock(rowcount=50)

        result = UsageMetricsAggregator.recalculate_token_split(
            db=mock_aggregator_db_session
        )

        assert "queries_updated" in result
        assert "metrics_updated" in result
        mock_aggregator_db_session.commit.assert_called_once()


class TestGetAggregationStatus:
    """Tests for get_aggregation_status method"""

    def test_get_status_with_data(self, mock_aggregator_db_session):
        """Test getting aggregation status"""
        today = date.today()

        # Mock aggregated dates
        aggregated_mock = MagicMock()
        aggregated_mock.date = today - timedelta(days=1)
        aggregated_mock.user_count = 25
        aggregated_mock.total_queries = 500

        query_mock = MagicMock()
        query_mock.filter.return_value = query_mock
        query_mock.group_by.return_value = query_mock
        query_mock.all.return_value = [aggregated_mock]

        mock_aggregator_db_session.query.return_value = query_mock

        result = UsageMetricsAggregator.get_aggregation_status(
            db=mock_aggregator_db_session, days=7
        )

        assert "period_start" in result
        assert "period_end" in result
        assert "aggregated_days" in result
        assert "missing_days" in result
        assert "daily_status" in result

    def test_get_status_identifies_gaps(self, mock_aggregator_db_session):
        """Test that missing days are identified"""
        # Mock no aggregated dates
        query_mock = MagicMock()
        query_mock.filter.return_value = query_mock
        query_mock.group_by.return_value = query_mock
        query_mock.all.return_value = []

        mock_aggregator_db_session.query.return_value = query_mock

        result = UsageMetricsAggregator.get_aggregation_status(
            db=mock_aggregator_db_session, days=7
        )

        # All days should be missing
        assert result["aggregated_days"] == 0
        assert result["missing_days"] == 8  # 7 days + today


class TestCostCalculation:
    """Tests for cost calculation logic"""

    def test_cost_calculation_formula(self):
        """Test cost is calculated correctly from tokens"""
        input_tokens = 10000
        output_tokens = 2000

        expected_cost = (
            input_tokens * UsageMetricsAggregator.INPUT_TOKEN_COST
            + output_tokens * UsageMetricsAggregator.OUTPUT_TOKEN_COST
        )

        # $0.0015 input + $0.0012 output = $0.0027
        assert expected_cost == pytest.approx(0.0027, rel=0.01)

    def test_token_estimation_80_20_split(self):
        """Test 80/20 split estimation"""
        total_tokens = 1000

        estimated_input = int(total_tokens * 0.8)
        estimated_output = total_tokens - estimated_input

        assert estimated_input == 800
        assert estimated_output == 200
        assert estimated_input + estimated_output == total_tokens
