"""
Optimal Legal Chunker cho văn bản pháp luật Việt Nam

Chunking strategy tối ưu kết hợp by_dieu và hierarchical_smart
"""

import re
import json
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

try:
    from .utils import TokenChecker
except ImportError:
    from utils import TokenChecker


@dataclass
class LawChunk:
    """Class đại diện cho một chunk văn bản luật"""

    chunk_id: str
    text: str
    metadata: Dict
    level: str  # 'chuong', 'dieu', 'khoan', 'diem'
    hierarchy: List[str]  # Path: ['Chương I', 'Điều 1', 'Khoản 1']
    char_count: int
    parent_id: str = None


class OptimalLegalChunker:
    """
    Chunking strategy tối ưu cho văn bản pháp luật Việt Nam
    Kết hợp ưu điểm của by_dieu và hierarchical_smart
    """

    def __init__(
        self,
        max_chunk_size: int = 2000,
        min_chunk_size: int = 300,
        token_limit: int = 6500,
        overlap_size: int = 150,
    ):
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.token_limit = token_limit
        self.overlap_size = overlap_size

        # Token checker for validation
        self.token_checker = TokenChecker(model="text-embedding-3-small")

        # Legal structure patterns
        self.patterns = {
            "chuong": r"^(CHƯƠNG [IVXLCDM]+|Chương [IVXLCDM]+)[:\.]?\s*(.+?)$",
            "dieu": r"^Điều\s+(\d+[a-z]?)\.\s*(.+?)$",
            "khoan": r"^(\d+)\.\s+(.+)",
            "diem": r"^([a-zđ])\)\s+(.+)",
        }

    def optimal_chunk_document(self, document: dict) -> List[LawChunk]:
        """Main method cho optimal chunking"""
        content = document.get("content", "")
        if isinstance(content, dict):
            content = content.get("full_text", "")

        metadata = document.get("metadata", {})
        if not metadata:
            metadata = document.get("info", {})

        print("🔄 Starting optimal chunking...")

        # Step 1: Base chunking by Điều
        base_chunks = self._chunk_by_dieu_with_context(content, metadata)
        print(f"   Step 1: {len(base_chunks)} base chunks created")

        # Step 2: Size optimization
        optimized_chunks = self._optimize_chunk_sizes(base_chunks, metadata)
        print(f"   Step 2: {len(optimized_chunks)} optimized chunks")

        # Step 3: Token validation and adjustment
        final_chunks = self._validate_and_adjust_tokens(optimized_chunks)
        print(f"   Step 3: {len(final_chunks)} final chunks")

        # Step 4: Quality enhancement
        enhanced_chunks = self._enhance_chunk_quality(final_chunks)
        print(f"   ✅ Optimal chunking complete: {len(enhanced_chunks)} chunks")

        return enhanced_chunks

    def _chunk_by_dieu_with_context(
        self, content: str, metadata: dict
    ) -> List[LawChunk]:
        """Chunk by Điều với context headers"""
        chunks = []

        # Split by Điều
        dieu_pattern = r"(Điều\s+\d+[a-z]?\.)"
        parts = re.split(dieu_pattern, content)

        current_chuong = ""
        current_section = ""

        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                dieu_header = parts[i].strip()
                dieu_content = parts[i + 1].strip()

                # Extract Điều number
                dieu_match = re.search(r"\d+[a-z]?", dieu_header)
                dieu_num = dieu_match.group() if dieu_match else str(i // 2)

                # Find current Chương
                for j in range(i, -1, -1):
                    content_part = parts[j].upper()
                    if "CHƯƠNG" in content_part:
                        chuong_match = re.search(r"(CHƯƠNG)\s+[IVXLCDM]+", content_part)
                        if chuong_match:
                            current_chuong = chuong_match.group()
                            break
                    # Also check for major sections
                    if any(
                        section in content_part
                        for section in [
                            "QUY ĐỊNH CHUNG",
                            "THỦ TỤC",
                            "QUẢN LÝ",
                            "XỬ PHẠT",
                        ]
                    ):
                        current_section = content_part.split("\n")[0].strip()

                # Build enhanced chunk text with context
                chunk_text = self._build_enhanced_chunk_text(
                    dieu_header, dieu_content, current_chuong, current_section
                )

                chunk = LawChunk(
                    chunk_id=f"optimal_dieu_{dieu_num}",
                    text=chunk_text,
                    metadata={
                        **metadata,
                        "dieu": dieu_num,
                        "chuong": current_chuong,
                        "section": current_section,
                        "chunking_strategy": "optimal_hybrid",
                    },
                    level="dieu",
                    hierarchy=[current_section, current_chuong, f"Điều {dieu_num}"],
                    char_count=len(chunk_text),
                )

                chunks.append(chunk)

        return chunks

    def _build_enhanced_chunk_text(
        self, dieu_header: str, dieu_content: str, chuong: str, section: str
    ) -> str:
        """Build chunk text with context headers"""
        context_parts = []

        if section:
            context_parts.append(f"[Phần: {section}]")
        if chuong:
            context_parts.append(f"[{chuong}]")

        context_header = " ".join(context_parts)

        if context_header:
            return f"{context_header}\n\n{dieu_header}\n\n{dieu_content}"
        else:
            return f"{dieu_header}\n\n{dieu_content}"

    def _optimize_chunk_sizes(
        self, chunks: List[LawChunk], metadata: dict
    ) -> List[LawChunk]:
        """Optimize chunk sizes based on limits"""
        optimized = []

        i = 0
        while i < len(chunks):
            chunk = chunks[i]

            if chunk.char_count > self.max_chunk_size:
                # Split large chunk by Khoản
                sub_chunks = self._split_large_chunk_by_khoan(chunk, metadata)
                optimized.extend(sub_chunks)

            elif chunk.char_count < self.min_chunk_size and i < len(chunks) - 1:
                # Try merge with next chunk
                next_chunk = chunks[i + 1]
                combined_size = chunk.char_count + next_chunk.char_count

                if combined_size <= self.max_chunk_size:
                    merged_chunk = self._merge_chunks(chunk, next_chunk, metadata)
                    optimized.append(merged_chunk)
                    i += 1  # Skip next chunk as it's merged
                else:
                    optimized.append(chunk)
            else:
                optimized.append(chunk)

            i += 1

        return optimized

    def _split_large_chunk_by_khoan(
        self, chunk: LawChunk, metadata: dict
    ) -> List[LawChunk]:
        """Split large chunk by Khoản"""
        sub_chunks = []
        content = chunk.text

        # Extract Điều info from chunk
        dieu_match = re.search(r"Điều\s+(\d+[a-z]?)", content)
        dieu_num = dieu_match.group(1) if dieu_match else "unknown"

        # Split by Khoản
        khoan_pattern = r"^(\d+)\.\s+"
        lines = content.split("\n")

        current_khoan = []
        khoan_num = 0
        context_header = ""

        # Extract context header
        for line in lines:
            if line.startswith("["):
                context_header += line + "\n"
            elif line.startswith("Điều"):
                context_header += line + "\n"
                break

        # Process Khoản
        in_content = False
        for line in lines:
            if line.startswith("Điều"):
                in_content = True
                continue

            if not in_content:
                continue

            if re.match(khoan_pattern, line):
                # Save previous Khoản
                if current_khoan:
                    khoan_text = (
                        context_header
                        + f"\nKhoản {khoan_num}:\n"
                        + "\n".join(current_khoan)
                    )

                    sub_chunk = LawChunk(
                        chunk_id=f"{chunk.chunk_id}_khoan_{khoan_num}",
                        text=khoan_text,
                        metadata={
                            **chunk.metadata,
                            "khoan": khoan_num,
                            "parent_dieu": dieu_num,
                        },
                        level="khoan",
                        hierarchy=chunk.hierarchy + [f"Khoản {khoan_num}"],
                        char_count=len(khoan_text),
                    )
                    sub_chunks.append(sub_chunk)

                # Start new Khoản
                khoan_match = re.match(khoan_pattern, line)
                khoan_num = int(khoan_match.group(1))
                current_khoan = [line]
            else:
                if current_khoan:  # Only add if we're in a Khoản
                    current_khoan.append(line)

        # Save last Khoản
        if current_khoan:
            khoan_text = (
                context_header + f"\nKhoản {khoan_num}:\n" + "\n".join(current_khoan)
            )

            sub_chunk = LawChunk(
                chunk_id=f"{chunk.chunk_id}_khoan_{khoan_num}",
                text=khoan_text,
                metadata={
                    **chunk.metadata,
                    "khoan": khoan_num,
                    "parent_dieu": dieu_num,
                },
                level="khoan",
                hierarchy=chunk.hierarchy + [f"Khoản {khoan_num}"],
                char_count=len(khoan_text),
            )
            sub_chunks.append(sub_chunk)

        return (
            sub_chunks if sub_chunks else [chunk]
        )  # Fallback to original if split failed

    def _merge_chunks(
        self, chunk1: LawChunk, chunk2: LawChunk, metadata: dict
    ) -> LawChunk:
        """Merge two chunks"""
        merged_text = f"{chunk1.text}\n\n{chunk2.text}"
        merged_hierarchy = chunk1.hierarchy + chunk2.hierarchy

        return LawChunk(
            chunk_id=f"{chunk1.chunk_id}_merged_{chunk2.chunk_id.split('_')[-1]}",
            text=merged_text,
            metadata={
                **chunk1.metadata,
                "merged_with": chunk2.chunk_id,
                "merged_dieu": [
                    chunk1.metadata.get("dieu", ""),
                    chunk2.metadata.get("dieu", ""),
                ],
            },
            level="merged_dieu",
            hierarchy=merged_hierarchy,
            char_count=len(merged_text),
        )

    def _validate_and_adjust_tokens(self, chunks: List[LawChunk]) -> List[LawChunk]:
        """Validate và adjust based on token limits"""
        validated = []

        for chunk in chunks:
            token_stats = self.token_checker.check_text(chunk.text)

            if token_stats.is_within_limit:
                # Add token info to metadata
                chunk.metadata["token_count"] = token_stats.token_count
                chunk.metadata["token_ratio"] = token_stats.ratio
                validated.append(chunk)
            else:
                # Try to split if over limit
                print(
                    f"   ⚠️ Chunk {chunk.chunk_id} over token limit ({token_stats.token_count} tokens)"
                )
                # For now, keep as is but mark as over-limit
                chunk.metadata["token_count"] = token_stats.token_count
                chunk.metadata["over_token_limit"] = True
                validated.append(chunk)

        return validated

    def _enhance_chunk_quality(self, chunks: List[LawChunk]) -> List[LawChunk]:
        """Final quality enhancement"""
        enhanced = []

        for chunk in chunks:
            # Add semantic tags
            chunk.metadata["semantic_tags"] = self._extract_semantic_tags(chunk.text)

            # Add readability score
            chunk.metadata["readability_score"] = self._calculate_readability_score(
                chunk.text
            )

            # Add structure info
            chunk.metadata["has_khoan"] = bool(
                re.search(r"^\d+\.", chunk.text, re.MULTILINE)
            )
            chunk.metadata["has_diem"] = bool(
                re.search(r"^[a-zđ]\)", chunk.text, re.MULTILINE)
            )

            enhanced.append(chunk)

        return enhanced

    def _extract_semantic_tags(self, text: str) -> List[str]:
        """Extract semantic tags từ content"""
        tags = []
        text_lower = text.lower()

        tag_patterns = {
            "registration": ["đăng ký", "đăng kí", "hệ thống mạng"],
            "timeline": ["thời gian", "thời hạn", "ngày", "tháng"],
            "procedures": ["thủ tục", "trình tự", "quy trình"],
            "documentation": ["hồ sơ", "tài liệu", "giấy tờ"],
            "management": ["quản lý", "giám sát", "kiểm tra"],
            "penalties": ["xử phạt", "vi phạm", "chế tài"],
            "requirements": ["yêu cầu", "điều kiện", "tiêu chuẩn"],
        }

        for tag, patterns in tag_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                tags.append(tag)

        return tags

    def _calculate_readability_score(self, text: str) -> float:
        """Simple readability score dựa trên structure"""
        lines = text.split("\n")
        non_empty_lines = [line for line in lines if line.strip()]

        if not non_empty_lines:
            return 0.0

        # Factors: shorter lines, clear structure, not too dense
        avg_line_length = sum(len(line) for line in non_empty_lines) / len(
            non_empty_lines
        )

        # Normalize to 0-1 scale (optimal around 80-120 chars per line)
        if 80 <= avg_line_length <= 120:
            readability = 1.0
        else:
            readability = max(0, 1 - abs(avg_line_length - 100) / 100)

        return min(1.0, readability)

    def export_to_jsonl(self, chunks: List[LawChunk], filename: str):
        """Export chunks sang JSONL format cho vector database"""
        with open(filename, "w", encoding="utf-8") as f:
            for chunk in chunks:
                record = {
                    "id": chunk.chunk_id,
                    "text": chunk.text,
                    "metadata": {
                        **chunk.metadata,
                        "level": chunk.level,
                        "hierarchy_path": " → ".join(chunk.hierarchy),
                        "char_count": chunk.char_count,
                    },
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        print(f"✅ Exported {len(chunks)} chunks to {filename}")
