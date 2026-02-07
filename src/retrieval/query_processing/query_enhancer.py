from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional
import os
import logging
import threading
from functools import lru_cache

from .strategies import (
    BaseEnhancementStrategy,
    MultiQueryStrategy,
    HyDEStrategy,
    StepBackStrategy,
    DecompositionStrategy,
)

from .complexity_analyzer import QuestionComplexityAnalyzer

logger = logging.getLogger(__name__)


class EnhancementStrategy(Enum):
    """Available enhancement strategies"""

    MULTI_QUERY = "multi_query"
    HYDE = "hyde"
    STEP_BACK = "step_back"
    DECOMPOSITION = "decomposition"


@dataclass
class QueryEnhancerConfig:
    """Configuration for QueryEnhancer"""

    llm_model: str = os.getenv("LLM_MODEL", "gemini-2.5-flash")
    temperature: float = 0.7
    max_queries: int = int(os.getenv("MAX_ENHANCED_QUERIES", "3"))
    strategies: List[EnhancementStrategy] = None
    enable_caching: bool = True
    use_complexity: bool = False  # Enable adaptive strategy selection

    def __post_init__(self):
        if self.strategies is None:
            self.strategies = [EnhancementStrategy.MULTI_QUERY]


# ===== SINGLETON CACHE FOR QUERY ENHANCERS =====
_enhancer_cache: Dict[str, "QueryEnhancer"] = {}
_enhancer_cache_lock = threading.Lock()


def get_cached_enhancer(
    strategies: List[EnhancementStrategy], max_queries: int = 3
) -> "QueryEnhancer":
    """
    Get a cached QueryEnhancer instance based on strategies.

    Thread-safe caching to avoid re-initializing LLM clients for each request.

    Args:
        strategies: List of enhancement strategies
        max_queries: Max queries for multi-query strategy

    Returns:
        Cached QueryEnhancer instance
    """
    # Create cache key from strategies
    key = "|".join(sorted(s.value for s in strategies)) + f"|{max_queries}"

    # Fast path: return cached instance
    if key in _enhancer_cache:
        logger.debug(f"📦 QueryEnhancer cache hit: {key}")
        return _enhancer_cache[key]

    # Slow path: create new instance with lock
    with _enhancer_cache_lock:
        # Double-check after acquiring lock
        if key not in _enhancer_cache:
            logger.info(f"🔧 Creating cached QueryEnhancer: {key}")
            config = QueryEnhancerConfig(
                strategies=list(strategies),
                max_queries=max_queries,
            )
            _enhancer_cache[key] = QueryEnhancer(config)
        return _enhancer_cache[key]


def clear_enhancer_cache():
    """Clear the enhancer cache (for testing only)."""
    global _enhancer_cache
    with _enhancer_cache_lock:
        _enhancer_cache.clear()
        logger.warning("⚠️ QueryEnhancer cache cleared")


class QueryEnhancer:
    def __init__(self, config: QueryEnhancerConfig):
        self.config = config
        self.analyzer = (
            QuestionComplexityAnalyzer() if hasattr(config, "use_complexity") else None
        )

        self.cache = {} if config.enable_caching else None

        self.strategies = self._init_strategies()
        logger.info(
            f"Initialized QueryEnhancer with strategies: {[s.value for s in self.strategies.keys()]}"
        )

    def _init_strategies(self) -> Dict:
        strategies = {}
        for strategy_type in self.config.strategies:
            try:
                if strategy_type == EnhancementStrategy.MULTI_QUERY:
                    strategies[strategy_type] = MultiQueryStrategy(
                        llm_model=self.config.llm_model,
                        temperature=0.7,
                        max_queries=self.config.max_queries,
                    )

                elif strategy_type == EnhancementStrategy.HYDE:
                    strategies[strategy_type] = HyDEStrategy(
                        llm_model=self.config.llm_model,
                        temperature=0.3,  # Lower temp for factual
                    )

                elif strategy_type == EnhancementStrategy.STEP_BACK:
                    strategies[strategy_type] = StepBackStrategy(
                        llm_model=self.config.llm_model, temperature=0.5
                    )

                elif strategy_type == EnhancementStrategy.DECOMPOSITION:
                    strategies[strategy_type] = DecompositionStrategy(
                        llm_model=self.config.llm_model,
                        temperature=0.7,
                        max_subqueries=self.config.max_queries,
                    )

                logger.info(f"Initialized {strategy_type.value} strategy")

            except Exception as e:
                logger.error(f"Failed to initialize {strategy_type.value}: {e}")

        return strategies

    def enhance(self, query: str) -> List[str]:
        """
        Main enhancement method

        Args:
            query: Original user query

        Returns:
            List of enhanced queries (including original)

        Process:
        1. Check cache
        2. Apply strategies
        3. Deduplicate
        4. Cache result
        5. Return"""
        if not query or not query.strip():
            logger.warning("Received empty query for enhancement")
            return [query]
        query = query.strip()

        if self.cache is not None and query in self.cache:
            logger.info("Cache hit for query")
            return self.cache[query]

        all_queries = [query]

        for strategy_type, strategy in self.strategies.items():
            try:
                logger.debug(f"Applying {strategy_type.value} strategy")
                enhanced = strategy.enhance(query)
                all_queries.extend(enhanced)
            except Exception as e:
                logger.error(f"Error applying {strategy_type.value}: {e}")

        result = self._deduplicate(all_queries)

        max_total = self.config.max_queries * len(self.strategies)
        result = result[:max_total]

        if self.cache is not None:
            self.cache[query] = result

        logger.info(f"Enhanced query to {len(result)} variations")
        return result

    def _deduplicate(self, queries: List[str]) -> List[str]:
        """
        Remove duplicate queries while preserving order

        Args:
            queries: List of queries (may contain duplicates)

        Returns:
            Deduplicated list
        """
        seen = set()
        result = []

        for q in queries:
            # Normalize for comparison (lowercase, strip)
            q_normalized = q.lower().strip()

            if q_normalized not in seen:
                seen.add(q_normalized)
                result.append(q)
        return result

    def clear_cache(self):
        """Clear cache (useful for testing or memory management)"""
        if self.cache is not None:
            self.cache.clear()
            logger.info("Cache cleared")

    def enhance_adaptive(self, query: str) -> List[str]:
        """
        Adaptive enhancement based on query complexity

        - Simple query → Multi-Query only
        - Moderate → Multi-Query + Step-Back
        - Complex → All strategies
        """
        if not self.analyzer:
            # Fallback to normal enhance
            return self.enhance(query)

        # Analyze complexity
        analysis = self.analyzer.analyze_question_complexity(query)
        complexity = analysis["complexity"]

        # Select strategies based on complexity
        if complexity == "simple":
            selected_strategies = [EnhancementStrategy.MULTI_QUERY]
        elif complexity == "moderate":
            selected_strategies = [
                EnhancementStrategy.MULTI_QUERY,
                EnhancementStrategy.STEP_BACK,
            ]
        else:  # complex
            selected_strategies = self.config.strategies

        # Apply selected strategies
        all_queries = [query]
        for strategy_type in selected_strategies:
            if strategy_type in self.strategies:
                try:
                    enhanced = self.strategies[strategy_type].enhance(query)
                    all_queries.extend(enhanced)
                except Exception as e:
                    logger.error(f"Strategy {strategy_type.value} failed: {e}")

        return self._deduplicate(all_queries)
