# src/retrieval/retrievers/adaptive_k_retriever.py

from typing import List
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun

from src.retrieval.query_processing.complexity_analyzer import (
    QuestionComplexityAnalyzer,
)
from .enhanced_retriever import EnhancedRetriever


class AdaptiveKRetriever(BaseRetriever):
    """
    Adaptive K retriever - adjust k based on question complexity.

    Complexity → K mapping:
    - SIMPLE: k=3
    - MODERATE: k=5
    - COMPLEX: k=8
    """

    enhanced_retriever: EnhancedRetriever
    k_min: int = 3
    k_max: int = 10
    complexity_analyzer: QuestionComplexityAnalyzer = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(
        self,
        enhanced_retriever: EnhancedRetriever,
        k_min: int = 3,
        k_max: int = 10,
        **kwargs,
    ):
        super().__init__(
            enhanced_retriever=enhanced_retriever, k_min=k_min, k_max=k_max, **kwargs
        )
        self.complexity_analyzer = QuestionComplexityAnalyzer()

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun | None = None,
    ) -> List[Document]:
        """Retrieve with adaptive k."""
        import logging

        logger = logging.getLogger(__name__)

        # Step 1: Analyze complexity (FIX: use correct method name)
        analysis = self.complexity_analyzer.analyze_question_complexity(query)
        logger.info(
            f"📊 Adaptive K: complexity={analysis.get('complexity')}, suggested_k={analysis.get('suggested_k')}"
        )

        # Step 2: Determine k based on complexity
        k = self._determine_k(analysis)
        logger.info(f"📊 Adaptive K: using k={k}")

        # Step 3: Update enhanced_retriever's k
        self.enhanced_retriever.k = k

        # Step 4: Retrieve
        return self.enhanced_retriever.invoke(query)

    def _determine_k(self, analysis: dict) -> int:
        """Map complexity to k value."""
        complexity = analysis.get("complexity", "MODERATE")
        suggested_k = analysis.get("suggested_k", 5)

        # Clamp to [k_min, k_max]
        return max(self.k_min, min(suggested_k, self.k_max))
