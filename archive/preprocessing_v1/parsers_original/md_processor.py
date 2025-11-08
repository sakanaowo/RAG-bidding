"""
Markdown Document Processor cho văn bản pháp luật

Xử lý .md files với YAML frontmatter và content pháp luật
"""

import re
import yaml
import os
from typing import Dict, List, Optional
from datetime import datetime

try:
    from .optimal_chunker import OptimalLegalChunker, LawChunk
    from .utils import TokenChecker
except ImportError:
    from optimal_chunker import OptimalLegalChunker, LawChunk
    from utils import TokenChecker


class MarkdownDocumentProcessor:
    """
    Processor chính để xử lý documents .md
    từ parsing YAML frontmatter đến chunking tối ưu
    """

    def __init__(
        self,
        max_chunk_size: int = 2000,
        min_chunk_size: int = 300,
        token_limit: int = 6500,
    ):
        self.chunker = OptimalLegalChunker(
            max_chunk_size=max_chunk_size,
            min_chunk_size=min_chunk_size,
            token_limit=token_limit,
            overlap_size=150,
        )
        self.token_checker = TokenChecker(model="text-embedding-3-large")

    def parse_md_file(self, file_path: str) -> dict:
        """Step 1: Parse .md file với YAML frontmatter"""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Tách YAML frontmatter và content
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                yaml_metadata = self._parse_yaml(parts[1])
                main_content = parts[2].strip()
            else:
                yaml_metadata = {}
                main_content = content
        else:
            yaml_metadata = {}
            main_content = content

        return {
            "metadata": yaml_metadata,
            "content": main_content,
            "file_path": file_path,
            "char_count": len(main_content),
            "processing_timestamp": datetime.now().isoformat(),
        }

    def _parse_yaml(self, yaml_content: str) -> dict:
        """Parse YAML frontmatter"""
        try:
            return yaml.safe_load(yaml_content) or {}
        except yaml.YAMLError:
            # Fallback to manual parsing
            metadata = {}
            for line in yaml_content.strip().split("\n"):
                if ":" in line and line.strip():
                    key, value = line.split(":", 1)
                    metadata[key.strip()] = value.strip().strip('"')
            return metadata

    def validate_document(self, document: dict) -> bool:
        """Step 2: Validate document structure"""
        content = document["content"]

        # Check for legal document patterns
        has_dieu = bool(re.search(r"Điều\s+\d+", content))
        has_chuong = bool(re.search(r"(CHƯƠNG|Chương)\s+[IVXLCDM]+", content))
        min_length = len(content) > 1000  # Minimum content length

        # Check for Vietnamese legal content
        legal_keywords = ["luật", "nghị định", "thông tư", "quyết định", "quy định"]
        has_legal_keywords = any(
            keyword in content.lower() for keyword in legal_keywords
        )

        validation = {
            "has_dieu": has_dieu,
            "has_chuong": has_chuong,
            "min_length": min_length,
            "has_legal_keywords": has_legal_keywords,
            "is_valid": has_dieu and min_length and has_legal_keywords,
        }

        document["validation"] = validation
        return validation["is_valid"]

    def process_to_chunks(self, document: dict) -> List[dict]:
        """Step 3: Apply optimal chunking strategy"""

        if not document.get("validation", {}).get("is_valid"):
            if not self.validate_document(document):
                raise ValueError("Document validation failed")

        # Apply optimal hybrid chunking
        chunks = self.chunker.optimal_chunk_document(document)

        # Convert to standard format
        processed_chunks = []
        for chunk in chunks:
            processed_chunk = {
                "id": chunk.chunk_id,
                "text": chunk.text,
                "metadata": {
                    **document["metadata"],  # Original metadata
                    **chunk.metadata,  # Chunk-specific metadata
                    "source_file": document["file_path"],
                    "chunk_level": chunk.level,
                    "hierarchy": " → ".join(chunk.hierarchy),
                    "char_count": chunk.char_count,
                    "semantic_tags": chunk.metadata.get("semantic_tags", []),
                },
            }
            processed_chunks.append(processed_chunk)

        return processed_chunks

    def validate_chunks(self, chunks: List[dict]) -> List[dict]:
        """Step 4: Validate và enhance chunk quality"""

        validated_chunks = []

        for chunk in chunks:
            # Token validation
            token_stats = self.token_checker.check_text(chunk["text"])

            chunk["metadata"].update(
                {
                    "token_count": token_stats.token_count,
                    "token_ratio": token_stats.ratio,
                    "is_within_token_limit": token_stats.is_within_limit,
                    "readability_score": self._calculate_readability(chunk["text"]),
                    "structure_score": self._calculate_structure_score(chunk["text"]),
                }
            )

            # Quality flags
            chunk["metadata"]["quality_flags"] = {
                "good_size": 300 <= chunk["metadata"]["char_count"] <= 2000,
                "good_tokens": token_stats.is_within_limit,
                "good_structure": chunk["metadata"]["structure_score"] > 0.7,
            }

            validated_chunks.append(chunk)

        return validated_chunks

    def _calculate_readability(self, text: str) -> float:
        """Tính điểm dễ đọc dựa trên cấu trúc"""
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if not lines:
            return 0.0

        avg_line_length = sum(len(line) for line in lines) / len(lines)
        # Optimal line length for Vietnamese legal text: 80-120 chars
        if 80 <= avg_line_length <= 120:
            return 1.0
        else:
            return max(0, 1 - abs(avg_line_length - 100) / 100)

    def _calculate_structure_score(self, text: str) -> float:
        """Tính điểm cấu trúc dựa trên legal patterns"""
        score = 0.0

        # Has clear hierarchy
        if re.search(r"^\d+\.", text, re.MULTILINE):
            score += 0.3
        if re.search(r"^[a-zđ]\)", text, re.MULTILINE):
            score += 0.2
        if "Điều" in text:
            score += 0.3
        if any(
            keyword in text.lower()
            for keyword in ["quy định", "trách nhiệm", "thủ tục"]
        ):
            score += 0.2

        return min(1.0, score)

    def export_for_vectordb(self, chunks: List[dict], output_path: str) -> int:
        """Step 5: Export chunks cho vector database"""
        try:
            from .utils import export_chunks_to_jsonl
        except ImportError:
            from utils import export_chunks_to_jsonl
        return export_chunks_to_jsonl(chunks, output_path)

    def generate_processing_report(self, chunks: List[dict]) -> dict:
        """Generate comprehensive processing report"""
        try:
            from .utils import generate_processing_report
        except ImportError:
            from utils import generate_processing_report
        return generate_processing_report(chunks)

    def process_single_file(self, file_path: str, output_dir: str = None) -> tuple:
        """
        Process một file .md duy nhất

        Returns:
            tuple: (chunks, report, output_file_path)
        """
        print(f"🔄 Processing single file: {os.path.basename(file_path)}")

        # Step 1-2: Parse và validate
        document = self.parse_md_file(file_path)

        if not self.validate_document(document):
            raise ValueError(f"Document validation failed for {file_path}")

        # Step 3: Chunk optimally
        chunks = self.process_to_chunks(document)
        print(f"   📊 Created {len(chunks)} chunks")

        # Step 4: Validate chunks
        validated_chunks = self.validate_chunks(chunks)
        print(f"   ✅ Validated {len(validated_chunks)} chunks")

        # Step 5: Export if output_dir provided
        output_file_path = None
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            filename = os.path.splitext(os.path.basename(file_path))[0]
            output_file_path = os.path.join(output_dir, f"{filename}_chunks.jsonl")
            self.export_for_vectordb(validated_chunks, output_file_path)
            print(f"   💾 Exported to: {output_file_path}")

        # Generate report
        report = self.generate_processing_report(validated_chunks)

        return validated_chunks, report, output_file_path

    def get_document_stats(self, document: dict) -> dict:
        """Get statistics về document"""
        content = document["content"]

        # Count structural elements
        dieu_count = len(re.findall(r"Điều\s+\d+[a-z]?\.", content))
        chuong_count = len(re.findall(r"(CHƯƠNG|Chương)\s+[IVXLCDM]+", content))
        khoan_count = len(re.findall(r"^\d+\.\s+", content, re.MULTILINE))
        diem_count = len(re.findall(r"^[a-zđ]\)\s+", content, re.MULTILINE))

        return {
            "char_count": len(content),
            "line_count": len(content.splitlines()),
            "word_count": len(content.split()),
            "dieu_count": dieu_count,
            "chuong_count": chuong_count,
            "khoan_count": khoan_count,
            "diem_count": diem_count,
            "estimated_tokens": len(content) / 2.8,  # Vietnamese estimate
            "structure_density": {
                "dieu_per_1000_chars": (
                    dieu_count / (len(content) / 1000) if content else 0
                ),
                "avg_chars_per_dieu": len(content) / dieu_count if dieu_count else 0,
            },
        }
