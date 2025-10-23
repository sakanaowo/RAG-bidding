"""
Quick test script for QueryEnhancer
"""

from src.retrieval.query_processing import (
    QueryEnhancer,
    QueryEnhancerConfig,
    EnhancementStrategy,
)

# Test 1: Basic initialization
print("Test 1: Basic Initialization")
print("=" * 50)

config = QueryEnhancerConfig(
    llm_model="gpt-4o-mini",
    strategies=[EnhancementStrategy.MULTI_QUERY],
    max_queries=3,
    enable_caching=True,
)

enhancer = QueryEnhancer(config)
print(f"✅ Enhancer initialized with {len(enhancer.strategies)} strategies")
print(f"✅ Caching enabled: {enhancer.cache is not None}")
print()

# Test 2: Multi-strategy
print("Test 2: Multiple Strategies")
print("=" * 50)

config_multi = QueryEnhancerConfig(
    strategies=[
        EnhancementStrategy.MULTI_QUERY,
        EnhancementStrategy.HYDE,
    ],
    max_queries=3,
)

enhancer_multi = QueryEnhancer(config_multi)
print(f"✅ Enhancer with {len(enhancer_multi.strategies)} strategies")
for strategy_type in enhancer_multi.strategies.keys():
    print(f"   - {strategy_type.value}")
print()

# Test 3: Enhancement (commented out - needs API key)
# print("Test 3: Query Enhancement")
# print("=" * 50)
# query = "Điều kiện tham gia đấu thầu là gì?"
# enhanced = enhancer.enhance(query)
# for i, q in enumerate(enhanced):
#     print(f"{i}. {q}")

print("\n✅ All imports and initialization tests passed!")
