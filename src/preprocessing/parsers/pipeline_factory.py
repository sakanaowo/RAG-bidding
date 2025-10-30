"""
Pipeline Factory - Auto-detect và select pipeline phù hợp

Automatically detects document type and returns appropriate pipeline
"""

import re
from pathlib import Path
from typing import Optional, Dict
from enum import Enum


class DocumentType(Enum):
    """Các loại văn bản được hỗ trợ"""

    LAW = "Luật"  # Luật
    DECREE = "Nghị định"  # Nghị định
    CIRCULAR = "Thông tư"  # Thông tư
    DECISION = "Quyết định"  # Quyết định
    FORM = "Biểu mẫu"  # Biểu mẫu, mẫu đơn
    TENDER = "Hồ sơ mời thầu"  # Tender documents
    CONTRACT = "Hợp đồng"  # Hợp đồng mẫu
    QA = "Câu hỏi"  # Câu hỏi thi
    UNKNOWN = "Unknown"


class DocumentTypeDetector:
    """Detect document type từ filename hoặc content"""

    def __init__(self):
        # Patterns để detect từ filename
        self.filename_patterns = {
            DocumentType.LAW: [
                r"(?i)luat.*\d+.*\d{4}",
                r"(?i)law.*\d+.*\d{4}",
                r"(?i)qh\d+",  # Quốc hội
            ],
            DocumentType.DECREE: [
                r"(?i)nghi.*dinh.*\d+.*\d{4}",
                r"(?i)nd[-_]?\d+",
                r"(?i)decree.*\d+",
            ],
            DocumentType.CIRCULAR: [
                r"(?i)thong.*tu.*\d+.*\d{4}",
                r"(?i)tt[-_]?\d+",
                r"(?i)circular.*\d+",
            ],
            DocumentType.DECISION: [
                r"(?i)quyet.*dinh.*\d+",
                r"(?i)qd[-_]?\d+",
                r"(?i)decision.*\d+",
            ],
            DocumentType.FORM: [
                r"(?i)bieu.*mau",
                r"(?i)mau.*\d+[a-z]?",
                r"(?i)form.*\d+",
                r"(?i)template",
            ],
            DocumentType.TENDER: [
                r"(?i)ho.*so.*moi.*thau",
                r"(?i)hsmt",
                r"(?i)hsyc",
                r"(?i)tender.*doc",
            ],
            DocumentType.CONTRACT: [
                r"(?i)hop.*dong",
                r"(?i)contract",
                r"(?i)agreement",
            ],
            DocumentType.QA: [
                r"(?i)cau.*hoi",
                r"(?i)question",
                r"(?i)exam",
                r"(?i)quiz",
            ],
        }

        # Patterns để detect từ content (first 2000 chars)
        self.content_patterns = {
            DocumentType.LAW: [
                r"QUỐC HỘI",
                r"Luật số \d+/\d{4}/QH",
                r"Căn cứ Hiến pháp",
            ],
            DocumentType.DECREE: [
                r"CHÍNH PHỦ",
                r"Nghị định số \d+/\d{4}/NĐ-CP",
                r"Căn cứ Luật",
            ],
            DocumentType.CIRCULAR: [
                r"THÔNG TƯ",
                r"Thông tư số \d+/\d{4}/TT",
                r"Hướng dẫn thi hành",
            ],
            DocumentType.DECISION: [
                r"QUYẾT ĐỊNH",
                r"Quyết định số \d+/\d{4}/QĐ",
                r"Về việc",
            ],
            DocumentType.FORM: [
                r"(?i)Biểu mẫu",
                r"(?i)Mẫu số \d+",
                r"(?i)Template",
            ],
            DocumentType.TENDER: [
                r"HỒ SƠ MỜI THẦU",
                r"HỒ SƠ YÊU CẦU",
                r"ĐIỀU KIỆN DỰ THẦU",
            ],
            DocumentType.CONTRACT: [
                r"HỢP ĐỒNG",
                r"ĐIỀU KHOẢN HỢP ĐỒNG",
                r"BÊN A",
                r"BÊN B",
            ],
            DocumentType.QA: [
                r"(?i)Câu \d+:",
                r"(?i)Question \d+:",
                r"(?i)Đáp án:",
                r"(?i)Answer:",
            ],
        }

    def detect_from_filename(self, filename: str) -> DocumentType:
        """Detect document type từ filename"""
        filename = Path(filename).stem.lower()

        for doc_type, patterns in self.filename_patterns.items():
            for pattern in patterns:
                if re.search(pattern, filename):
                    return doc_type

        return DocumentType.UNKNOWN

    def detect_from_content(self, content: str) -> DocumentType:
        """Detect document type từ content"""
        # Check first 2000 characters
        sample = content[:2000]

        scores = {doc_type: 0 for doc_type in DocumentType}

        for doc_type, patterns in self.content_patterns.items():
            for pattern in patterns:
                if re.search(pattern, sample, re.I):
                    scores[doc_type] += 1

        # Get type with highest score
        max_score = max(scores.values())
        if max_score > 0:
            for doc_type, score in scores.items():
                if score == max_score:
                    return doc_type

        return DocumentType.UNKNOWN

    def detect(
        self, file_path: Optional[str] = None, content: Optional[str] = None
    ) -> DocumentType:
        """
        Auto-detect document type

        Args:
            file_path: Path to file (optional)
            content: Document content (optional)

        Returns:
            DocumentType
        """
        # Try filename first
        if file_path:
            doc_type = self.detect_from_filename(file_path)
            if doc_type != DocumentType.UNKNOWN:
                return doc_type

        # Try content
        if content:
            doc_type = self.detect_from_content(content)
            if doc_type != DocumentType.UNKNOWN:
                return doc_type

        return DocumentType.UNKNOWN


class PipelineFactory:
    """
    Factory để tạo pipeline phù hợp cho từng loại văn bản
    """

    def __init__(self):
        self.detector = DocumentTypeDetector()
        self._pipelines = {}

    def create_pipeline(
        self,
        file_path: str,
        doc_type: Optional[str] = None,
        **kwargs,
    ):
        """
        Create pipeline phù hợp

        Args:
            file_path: Path to document
            doc_type: Document type (optional, auto-detect if None)
            **kwargs: Additional parameters for pipeline

        Returns:
            Appropriate pipeline instance
        """
        # Auto-detect if not provided
        if doc_type is None:
            detected_type = self.detector.detect(file_path=file_path)
        else:
            # Convert string to DocumentType
            detected_type = self._str_to_doctype(doc_type)

        # Create appropriate pipeline
        if detected_type == DocumentType.LAW:
            return self._create_law_pipeline(**kwargs)

        elif detected_type == DocumentType.DECREE:
            return self._create_decree_pipeline(**kwargs)

        elif detected_type == DocumentType.CIRCULAR:
            return self._create_circular_pipeline(**kwargs)

        elif detected_type == DocumentType.FORM:
            return self._create_form_pipeline(**kwargs)

        elif detected_type == DocumentType.TENDER:
            return self._create_tender_pipeline(**kwargs)

        elif detected_type == DocumentType.CONTRACT:
            return self._create_contract_pipeline(**kwargs)

        elif detected_type == DocumentType.QA:
            return self._create_qa_pipeline(**kwargs)

        else:
            # Default to law pipeline
            print(
                f"⚠️ Unknown document type, using default Law pipeline for: {file_path}"
            )
            return self._create_law_pipeline(**kwargs)

    def _str_to_doctype(self, doc_type_str: str) -> DocumentType:
        """Convert string to DocumentType"""
        mapping = {
            "luật": DocumentType.LAW,
            "law": DocumentType.LAW,
            "nghị định": DocumentType.DECREE,
            "decree": DocumentType.DECREE,
            "thông tư": DocumentType.CIRCULAR,
            "circular": DocumentType.CIRCULAR,
            "quyết định": DocumentType.DECISION,
            "decision": DocumentType.DECISION,
            "biểu mẫu": DocumentType.FORM,
            "form": DocumentType.FORM,
            "hồ sơ": DocumentType.TENDER,
            "tender": DocumentType.TENDER,
            "hợp đồng": DocumentType.CONTRACT,
            "contract": DocumentType.CONTRACT,
            "câu hỏi": DocumentType.QA,
            "qa": DocumentType.QA,
        }

        doc_type_lower = doc_type_str.lower().strip()
        return mapping.get(doc_type_lower, DocumentType.UNKNOWN)

    def _create_law_pipeline(self, **kwargs):
        """Create pipeline cho Luật"""
        from ..law_preprocessing import LawPreprocessingPipeline

        return LawPreprocessingPipeline(
            max_chunk_size=kwargs.get("max_chunk_size", 2000),
            min_chunk_size=kwargs.get("min_chunk_size", 300),
            aggressive_clean=kwargs.get("aggressive_clean", False),
        )

    def _create_decree_pipeline(self, **kwargs):
        """Create pipeline cho Nghị định"""
        from ..decree_preprocessing import DecreePreprocessingPipeline

        return DecreePreprocessingPipeline(
            chunk_size=kwargs.get("chunk_size", 512),
            chunk_overlap=kwargs.get("chunk_overlap", 50),
            output_dir=kwargs.get("output_dir", None),
        )

    def _create_circular_pipeline(self, **kwargs):
        """Create pipeline cho Thông tư"""
        # TODO: Implement CircularPipeline
        print("⚠️ Circular pipeline not implemented yet, using Law pipeline")
        return self._create_law_pipeline(**kwargs)

    def _create_form_pipeline(self, **kwargs):
        """Create pipeline cho Biểu mẫu"""
        # TODO: Implement FormPipeline
        print("⚠️ Form pipeline not implemented yet, using Law pipeline")
        return self._create_law_pipeline(**kwargs)

    def _create_tender_pipeline(self, **kwargs):
        """Create pipeline cho Hồ sơ mời thầu"""
        # TODO: Implement TenderPipeline
        print("⚠️ Tender pipeline not implemented yet, using Law pipeline")
        return self._create_law_pipeline(**kwargs)

    def _create_contract_pipeline(self, **kwargs):
        """Create pipeline cho Hợp đồng"""
        # TODO: Implement ContractPipeline
        print("⚠️ Contract pipeline not implemented yet, using Law pipeline")
        return self._create_law_pipeline(**kwargs)

    def _create_qa_pipeline(self, **kwargs):
        """Create pipeline cho Câu hỏi thi"""
        # TODO: Implement QAPipeline
        print("⚠️ QA pipeline not implemented yet, using Law pipeline")
        return self._create_law_pipeline(**kwargs)

    def get_supported_types(self) -> list[str]:
        """Get list of supported document types"""
        return [dt.value for dt in DocumentType if dt != DocumentType.UNKNOWN]


# ============ USAGE EXAMPLE ============

if __name__ == "__main__":
    from pathlib import Path

    factory = PipelineFactory()

    # Test files
    test_files = [
        "data/raw/Luat chinh/Luat Dau thau 2023.docx",
        "data/raw/Nghi dinh/ND 214 - 4.8.2025.docx",
        "data/raw/Thong tu/Thong tu 79-2025-BTC.docx",
        "data/raw/Bieu mau bao cao/Mau 01A.docx",
    ]

    print("=" * 80)
    print("PIPELINE FACTORY - AUTO DETECTION")
    print("=" * 80)

    for file_path in test_files:
        if not Path(file_path).exists():
            continue

        print(f"\n📄 File: {Path(file_path).name}")

        # Auto-detect
        detector = DocumentTypeDetector()
        doc_type = detector.detect(file_path=file_path)
        print(f"   🔍 Detected: {doc_type.value}")

        # Create pipeline
        pipeline = factory.create_pipeline(file_path)
        print(f"   ✅ Pipeline: {type(pipeline).__name__}")

    print(f"\n📋 Supported types: {', '.join(factory.get_supported_types())}")
