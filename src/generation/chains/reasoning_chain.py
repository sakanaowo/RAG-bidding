"""
Reasoning Chain - Chain of Thought Lite for RAG

2-step reasoning process:
1. Query Analysis: Extract intent, entities, and search strategy
2. Enhanced RAG: Use analysis to improve retrieval and response

This adds ~1s latency but improves answer quality for complex queries.
Enable with `use_cot=True` flag.
"""

import json
import logging
from typing import Dict, Any, Optional

from src.config.llm_provider import get_llm_client
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)


class ReasoningChain:
    """
    2-step Chain of Thought for RAG:
    1. Analyze query → extract intent, entities, strategy
    2. RAG with enhanced context from analysis
    """
    
    ANALYSIS_PROMPT = """Bạn là chuyên gia phân tích câu hỏi pháp luật đấu thầu Việt Nam.

Phân tích câu hỏi sau và trả lời bằng JSON:

Câu hỏi: {query}

Trả lời JSON (không markdown):
{{
    "intent_type": "factual|procedural|analytical|comparative",
    "key_entities": ["entity1", "entity2"],
    "required_info": ["info1", "info2"],
    "complexity": "simple|moderate|complex",
    "search_keywords": ["keyword1", "keyword2"],
    "suggested_approach": "Mô tả ngắn cách tiếp cận"
}}

Giải thích intent_type:
- factual: Hỏi về định nghĩa, khái niệm, con số cụ thể
- procedural: Hỏi về quy trình, thủ tục, các bước
- analytical: Hỏi về phân tích, so sánh, đánh giá
- comparative: So sánh giữa các điều khoản, văn bản"""

    def __init__(
        self,
        analyzer_model: str = "gpt-4o-mini",
        rag_mode: str = "balanced",
        analysis_timeout: int = 10,
    ):
        """
        Initialize ReasoningChain.
        
        Args:
            analyzer_model: Model for query analysis (fast model recommended)
            rag_mode: Mode for RAG pipeline
            analysis_timeout: Timeout for analysis step in seconds
        """
        # Use LLM provider factory (supports OpenAI, Gemini, Vertex AI)
        self.analyzer = get_llm_client(temperature=0)
        self.rag_mode = rag_mode
        self._prompt = ChatPromptTemplate.from_template(self.ANALYSIS_PROMPT)
        
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Step 1: Analyze query to extract intent and entities.
        
        Args:
            query: User query
            
        Returns:
            Analysis dict with intent, entities, complexity, etc.
        """
        try:
            chain = self._prompt | self.analyzer
            response = chain.invoke({"query": query})
            
            # Parse JSON response
            content = response.content.strip()
            # Handle markdown code blocks
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            analysis = json.loads(content)
            
            logger.info(
                f"🔍 Query Analysis: intent={analysis.get('intent_type')}, "
                f"complexity={analysis.get('complexity')}, "
                f"entities={analysis.get('key_entities', [])[:3]}"
            )
            
            return analysis
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse analysis JSON: {e}")
            return self._default_analysis(query)
        except Exception as e:
            logger.error(f"Query analysis failed: {e}")
            return self._default_analysis(query)
    
    def _default_analysis(self, query: str) -> Dict[str, Any]:
        """Return default analysis when parsing fails."""
        # Extract basic keywords from query
        keywords = [w for w in query.split() if len(w) > 2][:5]
        
        return {
            "intent_type": "factual",
            "key_entities": [],
            "required_info": [],
            "complexity": "simple",
            "search_keywords": keywords,
            "suggested_approach": "Direct retrieval"
        }
    
    def build_enhanced_prompt(
        self, 
        query: str, 
        analysis: Dict[str, Any]
    ) -> str:
        """
        Build enhanced query with analysis context.
        
        This gives the RAG pipeline more context about what to look for.
        """
        intent_descriptions = {
            "factual": "Tìm định nghĩa và thông tin cụ thể",
            "procedural": "Tìm quy trình và các bước thực hiện",
            "analytical": "Phân tích và đánh giá thông tin",
            "comparative": "So sánh các điều khoản hoặc quy định",
        }
        
        intent = analysis.get('intent_type', 'factual')
        intent_desc = intent_descriptions.get(intent, "Trả lời câu hỏi")
        
        key_entities = analysis.get('key_entities', [])
        required_info = analysis.get('required_info', [])
        approach = analysis.get('suggested_approach', '')
        
        enhanced = f"""[HƯỚNG DẪN TRẢ LỜI]
- Loại câu hỏi: {intent} - {intent_desc}
- Thực thể cần tập trung: {', '.join(key_entities) if key_entities else 'Không xác định'}
- Thông tin cần tìm: {', '.join(required_info) if required_info else 'Thông tin chung'}
- Cách tiếp cận: {approach}

[CÂU HỎI]
{query}"""
        
        return enhanced

    def invoke(
        self, 
        query: str,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run 2-step reasoning chain.
        
        Args:
            query: User query
            context: Optional conversation context
            
        Returns:
            Same format as qa_chain.answer() for compatibility,
            plus additional 'query_analysis' field.
        """
        # Import here to avoid circular imports
        from .qa_chain import answer as rag_answer
        
        # Step 1: Analyze query
        logger.info(f"🧠 CoT Step 1: Analyzing query...")
        analysis = self.analyze_query(query)
        
        # Step 2: Build enhanced prompt
        enhanced_query = self.build_enhanced_prompt(query, analysis)
        
        # Add conversation context if provided
        if context:
            enhanced_query = f"[CONTEXT HỘI THOẠI]\n{context}\n\n{enhanced_query}"
        
        # Step 3: RAG with enhanced query
        logger.info(f"🧠 CoT Step 2: Running RAG with enhanced prompt...")
        result = rag_answer(
            question=enhanced_query,
            mode=self.rag_mode,
            original_query=query,
        )
        
        # Add analysis to result for debugging/logging
        result["query_analysis"] = analysis
        result["cot_enabled"] = True
        
        return result


# Singleton instance for reuse
_reasoning_chain: Optional[ReasoningChain] = None


def get_reasoning_chain(mode: str = "balanced") -> ReasoningChain:
    """Get singleton ReasoningChain instance."""
    global _reasoning_chain
    if _reasoning_chain is None or _reasoning_chain.rag_mode != mode:
        _reasoning_chain = ReasoningChain(rag_mode=mode)
    return _reasoning_chain


def answer_with_reasoning(
    query: str,
    mode: str = "balanced",
    context: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Helper function: Answer with Chain of Thought reasoning.
    
    Usage:
        from src.generation.chains.reasoning_chain import answer_with_reasoning
        result = answer_with_reasoning("đấu thầu là gì?")
    """
    chain = get_reasoning_chain(mode)
    return chain.invoke(query, context)
