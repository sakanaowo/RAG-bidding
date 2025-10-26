import re
from typing import Dict, List
import math


class QuestionComplexityAnalyzer:
    def __init__(self):
        # Patterns for factual questions
        self.factual_patterns = [
            r"^(ai|gì|đâu|khi nào|bao nhiêu|như thế nào)",
            r"(là gì|nghĩa là gì|định nghĩa)",
            r"(năm nào|ngày nào|thời gian)",
        ]

        # Complex indicators
        self.complex_keywords = [
            "phân tích",
            "so sánh",
            "đánh giá",
            "giải thích",
            "tại sao",
            "như thế nào",
            "ảnh hưởng",
            "tác động",
            "mối quan hệ",
            "nguyên nhân",
            "hậu quả",
            "ưu nhược điểm",
            "khác biệt",
        ]

        # Simple indicators
        self.simple_keywords = [
            "là",
            "có",
            "được",
            "bao nhiêu",
            "ở đâu",
            "khi nào",
            "ai",
            "gì",
            "tên",
            "địa chỉ",
            "số điện thoại",
        ]

        # Question type patterns
        self.question_types = {
            "definition": [r"(là gì|nghĩa là gì|định nghĩa|ý nghĩa)"],
            "factual": [r"^(ai|gì|đâu|khi nào|bao nhiêu)"],
            "analytical": [r"(tại sao|vì sao|như thế nào|phân tích)"],
            "comparative": [r"(so sánh|khác nhau|giống nhau|tương tự)"],
            "evaluative": [r"(đánh giá|ưu điểm|nhược điểm|tốt|xấu)"],
        }

    def analyze_question_complexity(self, question: str) -> Dict:
        """Phân tích độ phức tạp của câu hỏi với nhiều tiêu chí"""
        question_lower = question.lower().strip()

        # Basic metrics
        word_count = len(question.split())
        char_count = len(question)

        # Pattern matching
        is_factual = self._check_factual_patterns(question_lower)
        question_type = self._identify_question_type(question_lower)

        # Keyword analysis
        complex_score = self._count_keywords(question_lower, self.complex_keywords)
        simple_score = self._count_keywords(question_lower, self.simple_keywords)

        # Structural analysis
        structural_complexity = self._analyze_structure(question)

        # Semantic analysis
        semantic_complexity = self._analyze_semantics(question_lower)

        # Calculate overall complexity
        complexity_metrics = {
            "word_count": word_count,
            "char_count": char_count,
            "complex_score": complex_score,
            "simple_score": simple_score,
            "structural_complexity": structural_complexity,
            "semantic_complexity": semantic_complexity,
            "is_factual": is_factual,
            "question_type": question_type,
        }

        # Determine final complexity level
        final_complexity = self._calculate_final_complexity(complexity_metrics)

        return {
            **complexity_metrics,
            "complexity": final_complexity["level"],
            "suggested_k": final_complexity["k_value"],
            "confidence_score": final_complexity["confidence"],
            "reasoning": final_complexity["reasoning"],
        }

    def _check_factual_patterns(self, question: str) -> bool:
        """Kiểm tra xem câu hỏi có phải dạng factual không"""
        return any(re.search(pattern, question) for pattern in self.factual_patterns)

    def _identify_question_type(self, question: str) -> str:
        """Xác định loại câu hỏi"""
        for q_type, patterns in self.question_types.items():
            if any(re.search(pattern, question) for pattern in patterns):
                return q_type
        return "general"

    def _count_keywords(self, question: str, keywords: List[str]) -> int:
        """Đếm số lượng keyword xuất hiện"""
        return sum(1 for keyword in keywords if keyword in question)

    def _analyze_structure(self, question: str) -> Dict:
        """Phân tích cấu trúc câu hỏi"""
        # Count clauses and conjunctions
        conjunctions = ["và", "hoặc", "nhưng", "tuy nhiên", "do đó", "vì vậy"]
        clause_indicators = [",", ";", ":", "-"]

        conjunction_count = sum(1 for conj in conjunctions if conj in question.lower())
        clause_count = sum(
            1 for indicator in clause_indicators if indicator in question
        )

        # Nested questions (questions within questions)
        nested_questions = question.count("?") > 1

        # Parenthetical information
        parenthetical = "(" in question and ")" in question

        return {
            "conjunction_count": conjunction_count,
            "clause_count": clause_count,
            "nested_questions": nested_questions,
            "parenthetical": parenthetical,
            "total_structural_score": conjunction_count
            + clause_count
            + int(nested_questions)
            + int(parenthetical),
        }

    def _analyze_semantics(self, question: str) -> Dict:
        """Phân tích ngữ nghĩa"""
        # Abstract vs concrete concepts
        abstract_indicators = [
            "khái niệm",
            "ý tưởng",
            "triết lý",
            "lý thuyết",
            "nguyên lý",
            "tư tưởng",
            "quan điểm",
            "góc nhìn",
            "cách nhìn",
        ]

        concrete_indicators = [
            "vật",
            "đồ vật",
            "địa điểm",
            "người",
            "thời gian",
            "số lượng",
            "kích thước",
            "màu sắc",
        ]

        abstract_score = self._count_keywords(question, abstract_indicators)
        concrete_score = self._count_keywords(question, concrete_indicators)

        # Domain-specific terminology
        technical_indicators = [
            "phương pháp",
            "quy trình",
            "thuật toán",
            "công thức",
            "kỹ thuật",
            "công nghệ",
            "hệ thống",
        ]

        technical_score = self._count_keywords(question, technical_indicators)

        return {
            "abstract_score": abstract_score,
            "concrete_score": concrete_score,
            "technical_score": technical_score,
            "abstraction_level": "high" if abstract_score > concrete_score else "low",
        }

    def _calculate_final_complexity(self, metrics: Dict) -> Dict:
        """Tính toán độ phức tạp cuối cùng"""
        # Weighted scoring
        weights = {
            "word_count": 0.15,
            "complex_score": 0.25,
            "simple_score": -0.20,  # Negative weight
            "structural_complexity": 0.20,
            "semantic_complexity": 0.15,
            "question_type_bonus": 0.05,
        }

        # Calculate base score
        structural_score = metrics["structural_complexity"]["total_structural_score"]
        semantic_score = (
            metrics["semantic_complexity"]["abstract_score"]
            + metrics["semantic_complexity"]["technical_score"]
        )

        # Normalize word count (longer questions tend to be more complex)
        normalized_word_count = min(metrics["word_count"] / 20.0, 1.0)

        # Question type bonus
        type_bonus = {
            "factual": 0,
            "definition": 1,
            "analytical": 3,
            "comparative": 2,
            "evaluative": 3,
            "general": 1,
        }.get(metrics["question_type"], 1)

        # Calculate weighted score
        score = (
            weights["word_count"] * normalized_word_count
            + weights["complex_score"] * metrics["complex_score"]
            + weights["simple_score"] * metrics["simple_score"]
            + weights["structural_complexity"] * structural_score
            + weights["semantic_complexity"] * semantic_score
            + weights["question_type_bonus"] * type_bonus
        )

        # Determine complexity level and confidence
        if score < 0.3:
            level = "simple"
            k_value = 2
            confidence = 0.8 if metrics["is_factual"] else 0.6
        elif score < 0.7:
            level = "moderate"
            k_value = 5
            confidence = 0.7
        else:
            level = "complex"
            k_value = 8
            confidence = 0.8

        # Generate reasoning
        reasoning = self._generate_reasoning(metrics, score)

        return {
            "level": level,
            "k_value": k_value,
            "confidence": confidence,
            "score": round(score, 3),
            "reasoning": reasoning,
        }

    def _generate_reasoning(self, metrics: Dict, score: float) -> str:
        """Tạo lý do giải thích về độ phức tạp"""
        factors = []

        if metrics["word_count"] > 15:
            factors.append(f"câu hỏi dài ({metrics['word_count']} từ)")

        if metrics["complex_score"] > 0:
            factors.append(f"chứa {metrics['complex_score']} từ khóa phức tạp")

        if metrics["structural_complexity"]["total_structural_score"] > 2:
            factors.append("cấu trúc câu phức tạp")

        if metrics["question_type"] in ["analytical", "evaluative"]:
            factors.append(f"thuộc dạng {metrics['question_type']}")

        if metrics["semantic_complexity"]["abstraction_level"] == "high":
            factors.append("yêu cầu tư duy trừu tượng")

        if not factors:
            return "Câu hỏi đơn giản, factual"

        return "Phức tạp do: " + ", ".join(factors)


# Example usage
if __name__ == "__main__":
    analyzer = QuestionComplexityAnalyzer()

    test_questions = [
        "Thủ đô của Việt Nam là gì?",
        "Phân tích so sánh ưu nhược điểm của các phương pháp machine learning trong xử lý ngôn ngữ tự nhiên",
        "Tại sao kinh tế Việt Nam phát triển nhanh trong thập kỷ qua?",
        "Bao nhiêu tỉnh thành ở Việt Nam?",
    ]

    for question in test_questions:
        result = analyzer.analyze_question_complexity(question)
        print(f"\nCâu hỏi: {question}")
        print(f"Độ phức tạp: {result['complexity']} (k={result['suggested_k']})")
        print(f"Độ tin cậy: {result['confidence_score']:.2f}")
        print(f"Lý do: {result['reasoning']}")
        print("-" * 50)
