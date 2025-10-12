from enum import Enum
import os
from typing import List


class EnhancementStrategy(Enum):
    MULTI_QUERY = "multi_query"
    HYDE = "hyde"
    STEP_BACK = "step_back"
    DECOMPOSITION = "decomposition"


@dataclass
class QueryEnhancerConfig:
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    temperature: float = 0.7
    max_queries: int = int(os.getenv("MAX_ENHANCED_QUERIES", "3"))
    strategies: List[EnhancementStrategy] = None
    enable_caching: bool = True

    def __post_init__(self):
        if self.strategies is None:
            self.strategies = [EnhancementStrategy.MULTI_QUERY]
