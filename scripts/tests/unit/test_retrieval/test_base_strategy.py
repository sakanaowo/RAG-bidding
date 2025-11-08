import pytest
from unittest.mock import Mock, patch
from src.retrieval.query_processing.strategies.base_strategy import (
    BaseEnhancementStrategy,
)


class DummyStrategy(BaseEnhancementStrategy):
    """Test implementation"""

    def enhance(self, query: str):
        return [query]


@pytest.fixture
def mock_strategy():
    """Create strategy with mocked LLM client"""
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        strategy = DummyStrategy("gpt-4o-mini")
        # Mock the client to avoid real API calls
        strategy.client = Mock()
        return strategy


def test_parse_numbered_list(mock_strategy):
    strategy = mock_strategy

    response = "1. First\n2. Second\n3. Third"
    result = strategy._parse_list_response(response)

    assert result == ["First", "Second", "Third"]


def test_parse_bulleted_list(mock_strategy):
    strategy = mock_strategy

    response = "- First\n- Second\n- Third"
    result = strategy._parse_list_response(response)

    assert result == ["First", "Second", "Third"]


def test_llm_call(mock_strategy):
    """Test LLM call with mocked response"""
    strategy = mock_strategy

    # Mock response
    mock_response = Mock()
    mock_response.content = "Hello World"
    strategy.client.invoke.return_value = mock_response

    response = strategy._call_llm(
        system_prompt="You are a helpful assistant", user_prompt="Say 'Hello World'"
    )

    assert response == "Hello World"
    strategy.client.invoke.assert_called_once()


def test_parse_mixed_format(mock_strategy):
    """Test parsing mixed numbered and bulleted list"""
    strategy = mock_strategy

    response = "1. First item\n- Second item\n3. Third item"
    result = strategy._parse_list_response(response)

    assert result == ["First item", "Second item", "Third item"]


def test_parse_empty_response(mock_strategy):
    """Test parsing empty response"""
    strategy = mock_strategy

    assert strategy._parse_list_response("") == []
    assert strategy._parse_list_response("   ") == []
    assert strategy._parse_list_response("\n\n") == []


def test_parse_with_extra_whitespace(mock_strategy):
    """Test parsing with extra whitespace"""
    strategy = mock_strategy

    response = "  1.   First  \n\n  2.  Second  \n   3. Third   "
    result = strategy._parse_list_response(response)

    assert result == ["First", "Second", "Third"]


def test_parse_vietnamese_content(mock_strategy):
    """Test parsing Vietnamese content"""
    strategy = mock_strategy

    response = (
        "1. Điều kiện tham gia đấu thầu\n2. Yêu cầu về năng lực\n3. Hồ sơ dự thầu"
    )
    result = strategy._parse_list_response(response)

    assert len(result) == 3
    assert "Điều kiện tham gia đấu thầu" in result
    assert "Yêu cầu về năng lực" in result
