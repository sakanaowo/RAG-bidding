import re
import json
from typing import List, Dict, Tuple
from dataclasses import dataclass


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


class LegalDocumentChunker:
    """Chunking chuyên biệt cho văn bản pháp luật"""

    def __init__(
        self,
        strategy: str = "hierarchical",
        max_chunk_size: int = 1500,
        overlap_size: int = 200,
        keep_parent_context: bool = True,
    ):
        """
        Args:
            strategy: 'hierarchical', 'by_dieu', 'by_khoan', 'hybrid'
            max_chunk_size: Kích thước tối đa của chunk (ký tự)
            overlap_size: Overlap giữa các chunks liền kề
            keep_parent_context: Có giữ context của phần tử cha không
        """
        self.strategy = strategy
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
        self.keep_parent_context = keep_parent_context

        # Regex patterns cho các cấu trúc luật
        self.patterns = {
            "chuong": r"^(CHƯƠNG [IVXLCDM]+|Chương [IVXLCDM]+)[:\.]?\s*(.+?)$",
            "dieu": r"^Điều\s+(\d+[a-z]?)\.\s*(.+?)$",
            "khoan": r"^(\d+)\.\s+(.+)",
            "diem": r"^([a-zđ])\)\s+(.+)",
        }

    def chunk_document(self, document: Dict) -> List[LawChunk]:
        """Main method để chunk document"""

        if self.strategy == "hierarchical":
            return self._hierarchical_chunking(document)
        elif self.strategy == "by_dieu":
            return self._chunk_by_dieu(document)
        elif self.strategy == "by_khoan":
            return self._chunk_by_khoan(document)
        elif self.strategy == "hybrid":
            return self._hybrid_chunking(document)
        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")

    def _hierarchical_chunking(self, document: Dict) -> List[LawChunk]:
        """
        Chunking theo cấu trúc phân cấp:
        - Chương → Điều → Khoản → Điểm
        """
        chunks = []
        content = document.get("content", {}).get("full_text", "")
        metadata = document.get("info", {})

        # Parse cấu trúc văn bản
        structure = self._parse_structure(content)

        # Tạo chunks theo từng Điều (level tối ưu)
        doc_id = self._generate_doc_id(metadata)

        for item in structure:
            if item["type"] == "dieu":
                chunk_text = self._build_chunk_with_context(item, structure)

                chunk = LawChunk(
                    chunk_id=f"{doc_id}_{item['dieu_num']}",
                    text=chunk_text,
                    metadata={
                        **metadata,
                        "dieu": item["dieu_num"],
                        "dieu_title": item.get("title", ""),
                        "chuong": item.get("chuong", ""),
                    },
                    level="dieu",
                    hierarchy=item.get("hierarchy", []),
                    char_count=len(chunk_text),
                )

                chunks.append(chunk)

                # Nếu Điều quá dài, chia nhỏ theo Khoản
                if len(chunk_text) > self.max_chunk_size:
                    sub_chunks = self._split_large_dieu(item, doc_id, metadata)
                    chunks.extend(sub_chunks)

        return chunks

    def _chunk_by_dieu(self, document: Dict) -> List[LawChunk]:
        """Chunk theo từng Điều - đơn giản và hiệu quả"""
        chunks = []
        content = document.get("content", {}).get("full_text", "")
        metadata = document.get("info", {})
        doc_id = self._generate_doc_id(metadata)

        # Split theo "Điều X"
        dieu_pattern = r"(Điều\s+\d+[a-z]?\.)"
        parts = re.split(dieu_pattern, content)

        current_chuong = ""

        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                dieu_header = parts[i].strip()
                dieu_content = parts[i + 1].strip()

                # Extract số Điều
                dieu_num = re.search(r"\d+[a-z]?", dieu_header)
                dieu_num = dieu_num.group() if dieu_num else str(i // 2)

                # Tìm Chương hiện tại (nếu có)
                for j in range(i, -1, -1):
                    if "CHƯƠNG" in parts[j].upper() or "Chương" in parts[j]:
                        current_chuong = re.search(
                            r"(CHƯƠNG|Chương)\s+[IVXLCDM]+", parts[j]
                        )
                        current_chuong = (
                            current_chuong.group() if current_chuong else ""
                        )
                        break

                chunk_text = f"{dieu_header}\n\n{dieu_content}"

                chunk = LawChunk(
                    chunk_id=f"{doc_id}_dieu_{dieu_num}",
                    text=chunk_text,
                    metadata={
                        **metadata,
                        "dieu": dieu_num,
                        "chuong": current_chuong,
                    },
                    level="dieu",
                    hierarchy=(
                        [current_chuong, dieu_header]
                        if current_chuong
                        else [dieu_header]
                    ),
                    char_count=len(chunk_text),
                )

                chunks.append(chunk)

        return chunks

    def _chunk_by_khoan(self, document: Dict) -> List[LawChunk]:
        """Chunk chi tiết theo từng Khoản"""
        chunks = []
        content = document.get("content", {}).get("full_text", "")
        metadata = document.get("info", {})
        doc_id = self._generate_doc_id(metadata)

        # Parse structure
        structure = self._parse_structure(content)

        for dieu in structure:
            if dieu["type"] == "dieu":
                dieu_content = dieu["content"]

                # Split theo khoản (số đầu dòng)
                khoan_pattern = r"^(\d+)\.\s+"
                lines = dieu_content.split("\n")

                current_khoan = []
                khoan_num = 0

                for line in lines:
                    if re.match(khoan_pattern, line):
                        # Save previous khoan
                        if current_khoan:
                            chunk_text = self._build_khoan_chunk(
                                dieu, khoan_num, current_khoan
                            )

                            chunk = LawChunk(
                                chunk_id=f"{doc_id}_dieu_{dieu['dieu_num']}_khoan_{khoan_num}",
                                text=chunk_text,
                                metadata={
                                    **metadata,
                                    "dieu": dieu["dieu_num"],
                                    "khoan": khoan_num,
                                    "chuong": dieu.get("chuong", ""),
                                },
                                level="khoan",
                                hierarchy=dieu.get("hierarchy", [])
                                + [f"Khoản {khoan_num}"],
                                char_count=len(chunk_text),
                            )
                            chunks.append(chunk)

                        # Start new khoan
                        khoan_num = int(re.match(khoan_pattern, line).group(1))
                        current_khoan = [line]
                    else:
                        current_khoan.append(line)

                # Save last khoan
                if current_khoan:
                    chunk_text = self._build_khoan_chunk(dieu, khoan_num, current_khoan)
                    chunk = LawChunk(
                        chunk_id=f"{doc_id}_dieu_{dieu['dieu_num']}_khoan_{khoan_num}",
                        text=chunk_text,
                        metadata={
                            **metadata,
                            "dieu": dieu["dieu_num"],
                            "khoan": khoan_num,
                        },
                        level="khoan",
                        hierarchy=dieu.get("hierarchy", []) + [f"Khoản {khoan_num}"],
                        char_count=len(chunk_text),
                    )
                    chunks.append(chunk)

        return chunks

    def _hybrid_chunking(self, document: Dict) -> List[LawChunk]:
        """
        Chunking lai:
        - Điều ngắn: giữ nguyên
        - Điều dài: chia theo Khoản
        - Thêm overlap context
        """
        chunks = []
        content = document.get("content", {}).get("full_text", "")
        metadata = document.get("info", {})
        doc_id = self._generate_doc_id(metadata)

        structure = self._parse_structure(content)

        for idx, dieu in enumerate(structure):
            if dieu["type"] == "dieu":
                dieu_text = self._build_chunk_with_context(dieu, structure)

                # Nếu Điều ngắn, giữ nguyên
                if len(dieu_text) <= self.max_chunk_size:
                    chunk = LawChunk(
                        chunk_id=f"{doc_id}_dieu_{dieu['dieu_num']}",
                        text=dieu_text,
                        metadata={**metadata, "dieu": dieu["dieu_num"]},
                        level="dieu",
                        hierarchy=dieu.get("hierarchy", []),
                        char_count=len(dieu_text),
                    )
                    chunks.append(chunk)
                else:
                    # Điều dài: chia theo Khoản với overlap
                    khoan_chunks = self._split_with_overlap(dieu, doc_id, metadata)
                    chunks.extend(khoan_chunks)

        return chunks

    # ============ HELPER METHODS ============

    def _parse_structure(self, content: str) -> List[Dict]:
        """Parse cấu trúc văn bản thành hierarchy"""
        structure = []
        lines = content.split("\n")

        current_chuong = ""
        current_dieu = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for Chương
            chuong_match = re.match(self.patterns["chuong"], line, re.IGNORECASE)
            if chuong_match:
                current_chuong = line
                continue

            # Check for Điều
            dieu_match = re.match(self.patterns["dieu"], line)
            if dieu_match:
                if current_dieu:
                    structure.append(current_dieu)

                current_dieu = {
                    "type": "dieu",
                    "dieu_num": dieu_match.group(1),
                    "title": dieu_match.group(2),
                    "chuong": current_chuong,
                    "content": "",
                    "hierarchy": (
                        [current_chuong, f"Điều {dieu_match.group(1)}"]
                        if current_chuong
                        else [f"Điều {dieu_match.group(1)}"]
                    ),
                }
                continue

            # Add to current Điều
            if current_dieu:
                current_dieu["content"] += line + "\n"

        # Add last Điều
        if current_dieu:
            structure.append(current_dieu)

        return structure

    def _build_chunk_with_context(self, dieu: Dict, structure: List[Dict]) -> str:
        """Build chunk với parent context"""
        chunk_text = f"Điều {dieu['dieu_num']}. {dieu['title']}\n\n"

        # Thêm context Chương nếu có
        if self.keep_parent_context and dieu.get("chuong"):
            chunk_text = f"[Context: {dieu['chuong']}]\n\n" + chunk_text

        chunk_text += dieu["content"]

        return chunk_text.strip()

    def _build_khoan_chunk(
        self, dieu: Dict, khoan_num: int, khoan_lines: List[str]
    ) -> str:
        """Build chunk cho một khoản"""
        chunk_text = f"Điều {dieu['dieu_num']}. {dieu.get('title', '')}\n\n"
        chunk_text += f"Khoản {khoan_num}:\n"
        chunk_text += "\n".join(khoan_lines)

        return chunk_text.strip()

    def _split_large_dieu(
        self, dieu: Dict, doc_id: str, metadata: Dict
    ) -> List[LawChunk]:
        """Chia Điều quá dài thành nhiều chunks nhỏ"""
        chunks = []
        content = dieu["content"]

        # Split theo khoản
        khoan_pattern = r"^(\d+)\.\s+"
        parts = re.split(f"({khoan_pattern})", content, flags=re.MULTILINE)

        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                khoan_header = parts[i]
                khoan_content = parts[i + 1]

                chunk_text = f"Điều {dieu['dieu_num']}. {dieu.get('title', '')}\n\n"
                chunk_text += khoan_header + khoan_content

                chunk = LawChunk(
                    chunk_id=f"{doc_id}_dieu_{dieu['dieu_num']}_sub_{i//2}",
                    text=chunk_text,
                    metadata={
                        **metadata,
                        "dieu": dieu["dieu_num"],
                        "sub_chunk": i // 2,
                    },
                    level="khoan",
                    hierarchy=dieu.get("hierarchy", []) + [f"Khoản {i//2}"],
                    char_count=len(chunk_text),
                )
                chunks.append(chunk)

        return chunks

    def _split_with_overlap(
        self, dieu: Dict, doc_id: str, metadata: Dict
    ) -> List[LawChunk]:
        """Chia chunk với overlap"""
        chunks = []
        content = dieu["content"]

        # Simple overlapping split
        start = 0
        chunk_idx = 0

        while start < len(content):
            end = start + self.max_chunk_size
            chunk_content = content[start:end]

            chunk_text = (
                f"Điều {dieu['dieu_num']}. {dieu.get('title', '')}\n\n{chunk_content}"
            )

            chunk = LawChunk(
                chunk_id=f"{doc_id}_dieu_{dieu['dieu_num']}_part_{chunk_idx}",
                text=chunk_text,
                metadata={**metadata, "dieu": dieu["dieu_num"], "part": chunk_idx},
                level="dieu_part",
                hierarchy=dieu.get("hierarchy", []),
                char_count=len(chunk_text),
            )
            chunks.append(chunk)

            start = end - self.overlap_size
            chunk_idx += 1

        return chunks

    def _generate_doc_id(self, metadata: Dict) -> str:
        """Tạo document ID"""
        number = metadata.get("number", "")
        if number:
            return re.sub(r"[^\w\-]", "-", number.lower()).strip("-")
        return "doc"

    def export_chunks_to_jsonl(self, chunks: List[LawChunk], filename: str):
        """Export chunks sang JSONL cho vector database"""
        with open(filename, "w", encoding="utf-8") as f:
            for chunk in chunks:
                record = {
                    "id": chunk.chunk_id,
                    "text": chunk.text,
                    "metadata": {
                        **chunk.metadata,
                        "level": chunk.level,
                        "hierarchy": " > ".join(chunk.hierarchy),
                        "char_count": chunk.char_count,
                    },
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        print(f"Exported {len(chunks)} chunks into {filename}")

    def get_chunking_stats(self, chunks: List[LawChunk]) -> Dict:
        """Thống kê về chunks"""
        stats = {
            "total_chunks": len(chunks),
            "avg_chunk_size": (
                sum(c.char_count for c in chunks) / len(chunks) if chunks else 0
            ),
            "min_chunk_size": min(c.char_count for c in chunks) if chunks else 0,
            "max_chunk_size": max(c.char_count for c in chunks) if chunks else 0,
            "by_level": {},
        }

        # Count by level
        for chunk in chunks:
            level = chunk.level
            if level not in stats["by_level"]:
                stats["by_level"][level] = 0
            stats["by_level"][level] += 1

        return stats


# ============ USAGE EXAMPLE ============

if __name__ == "__main__":
    # Load document
    with open("data/nghi_dinh_214.json", "r", encoding="utf-8") as f:
        document = json.load(f)

    print("=" * 80)
    print("CHUNKING STRATEGIES FOR LEGAL DOCUMENTS")
    print("=" * 80)

    strategies = ["by_dieu", "by_khoan", "hierarchical", "hybrid"]

    for strategy in strategies:
        print(f"\n{'='*80}")
        print(f"STRATEGY: {strategy.upper()}")
        print(f"{'='*80}")

        chunker = LegalDocumentChunker(
            strategy=strategy,
            max_chunk_size=1500,
            overlap_size=200,
            keep_parent_context=True,
        )

        chunks = chunker.chunk_document(document)

        # Statschunk-strategedy
        stats = chunker.get_chunking_stats(chunks)
        print(f"\n📊 Thống kê:")
        print(f"  - Tổng chunks: {stats['total_chunks']}")
        print(f"  - Kích thước trung bình: {stats['avg_chunk_size']:.0f} ký tự")
        print(f"  - Min/Max: {stats['min_chunk_size']}/{stats['max_chunk_size']} ký tự")
        print(f"  - Phân bổ theo level: {stats['by_level']}")

        # Export
        chunker.export_chunks_to_jsonl(chunks, f"data/rag/{strategy}_chunks.jsonl")

        # Show sample
        print(f"\n📝 Sample chunk:")
        if chunks:
            sample = chunks[0]
            print(f"  ID: {sample.chunk_id}")
            print(f"  Hierarchy: {' > '.join(sample.hierarchy)}")
            print(f"  Text preview: {sample.text[:200]}...")

    print("\n" + "=" * 80)
    print("HOÀN THÀNH!")
    print("=" * 80)
