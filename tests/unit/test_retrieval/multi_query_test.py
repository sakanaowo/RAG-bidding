import pytest
from src.retrieval.query_processing.strategies.multi_query import MultiQueryStrategy


def test_multi_query_generates_variations(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")

    def fake_call_llm(self, system_prompt, user_prompt):
        return "Bản 1\nBản 2\nBản 3"

    monkeypatch.setattr(MultiQueryStrategy, "_call_llm", fake_call_llm)

    strategy = MultiQueryStrategy("gpt-4o-mini", temperature=0.7, max_queries=3)
    variations = strategy.enhance("Điều kiện tham gia đấu thầu là gì?")

    assert variations[0] == "Điều kiện tham gia đấu thầu là gì?"
    assert len(variations) == 4
