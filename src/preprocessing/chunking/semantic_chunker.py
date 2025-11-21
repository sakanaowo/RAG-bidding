"""
Semantic chunking for non-hierarchical documents.

Strategy:
- Chunk by semantic units (sections, forms, questions)
- Preserve context and structure
- Handle tables and lists specially

Supports:
- Bidding documents (11 types: HSMT, HSDT, HSYC, etc.)
- Reports (5 types: BC_DANH_GIA, etc.)
- Exam questions (PDF)
"""

import re
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

from src.preprocessing.chunking.base_chunker import BaseLegalChunker, UniversalChunk
from src.preprocessing.base.models import ProcessedDocument


class SemanticChunker(BaseLegalChunker):
    """
    Semantic chunking for bidding, report, and exam documents.

    Unlike HierarchicalChunker (Điều-based), this chunker identifies
    semantic boundaries based on document type:

    Bidding:
    - Section-based (I., II., III., etc.)
    - Form-based (Biểu mẫu 1, Mẫu số 2, etc.)
    - Table-aware (preserve complete tables)

    Reports:
    - PHẦN-based (PHẦN I, PHẦN II)
    - Subsection-based (1.1, 1.2, 2.1, etc.)
    - Table-aware

    Exam:
    - Question-based (Câu 1, Câu 2, etc.)
    - One question = one chunk (usually 200-500 chars)
    - Include question + all answer choices
    """

    # Patterns for different document types
    BIDDING_PATTERNS = {
        "section": r"^([IVXLCDM]+|[A-Z])\.\s+(.+)$",  # I., II., A., B.
        "subsection": r"^(\d+)\.\s+(.+)$",  # 1., 2., 3.
        "form": r"^(Biểu mẫu|Mẫu số|Phụ lục)\s+(\d+[A-Z]?)[:\.]?\s*(.*)$",
        "table_start": r"^(Bảng|Table)\s+(\d+)",
    }

    REPORT_PATTERNS = {
        "phan": r"^(PHẦN|Phần)\s+([IVXLCDM]+|[A-Z])[:\.]?\s*(.+)$",
        "section": r"^(\d+)\.\s+(.+)$",  # 1., 2.
        "subsection": r"^(\d+\.\d+)\.\s+(.+)$",  # 1.1., 2.3.
        "table_start": r"^(Bảng|Table)\s+(\d+)",
    }

    EXAM_PATTERNS = {
        "question": r"^(Câu|Question)\s+(\d+)[:\.]?\s*(.*)$",
        "answer": r"^([A-D])\.\s+(.+)$",
    }

    def __init__(
        self,
        document_type: str = "bidding",  # bidding, report, exam
        min_size: int = 300,
        max_size: int = 1500,
        target_size: int = 800,
        overlap: int = 100,
        preserve_context: bool = True,
        preserve_tables: bool = True,
    ):
        """
        Args:
            document_type: Type of document (bidding, report, exam)
            preserve_tables: Keep complete tables in single chunk
        """
        super().__init__(min_size, max_size, target_size, overlap, preserve_context)

        self.document_type = document_type.lower()
        self.preserve_tables = preserve_tables

        # Select patterns based on document type
        if self.document_type == "bidding":
            self.patterns = self.BIDDING_PATTERNS
        elif self.document_type == "report":
            self.patterns = self.REPORT_PATTERNS
        elif self.document_type == "exam":
            self.patterns = self.EXAM_PATTERNS
        else:
            raise ValueError(f"Unsupported document type: {document_type}")

    def chunk(self, document: ProcessedDocument) -> List[UniversalChunk]:
        """
        Chunk document based on semantic boundaries.

        Args:
            document: ProcessedDocument from loader

        Returns:
            List of UniversalChunk objects
        """
        # Get full text
        full_text = document.content.get("full_text", "")
        if not full_text:
            return []

        # Clean text
        full_text = self._clean_text(full_text)

        # Get document ID from metadata or generate if not present
        doc_id = document.metadata.get("document_id")
        if not doc_id:
            doc_id = self._generate_document_id(document)

        # Route to appropriate chunking method
        if self.document_type == "exam":
            chunks = self._chunk_exam(full_text, document, doc_id)
        elif self.document_type == "report":
            chunks = self._chunk_report(full_text, document, doc_id)
        elif self.document_type == "bidding":
            chunks = self._chunk_bidding(full_text, document, doc_id)
        else:
            raise ValueError(f"Unknown document type: {self.document_type}")

        # Update statistics
        self._update_statistics(chunks)

        return chunks

    # ============================================================
    # EXAM CHUNKING (Question-based)
    # ============================================================

    def _chunk_exam(
        self,
        text: str,
        document: ProcessedDocument,
        doc_id: str,
    ) -> List[UniversalChunk]:
        """
        Chunk exam questions.

        Strategy:
        - One question + all answers = one chunk
        - Usually 200-500 chars per question
        - No splitting (keep semantic unit intact)

        Args:
            text: Full exam text
            document: ProcessedDocument
            doc_id: Document ID

        Returns:
            List of chunks (one per question)
        """
        lines = text.split("\n")
        chunks = []

        current_question = None
        current_answers = []
        chunk_index = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for question
            question_match = re.match(self.patterns["question"], line)
            if question_match:
                # Save previous question
                if current_question:
                    chunk = self._create_exam_chunk(
                        question=current_question,
                        answers=current_answers,
                        document=document,
                        doc_id=doc_id,
                        chunk_index=chunk_index,
                    )
                    chunks.append(chunk)
                    chunk_index += 1

                # Start new question
                question_num = question_match.group(2)
                question_text = question_match.group(3).strip()

                current_question = {
                    "number": question_num,
                    "text": line if question_text else "",
                    "full_line": line,
                }
                current_answers = []
                continue

            # Check for answer
            answer_match = re.match(self.patterns["answer"], line)
            if answer_match and current_question:
                answer_letter = answer_match.group(1)
                answer_text = answer_match.group(2)
                current_answers.append(
                    {
                        "letter": answer_letter,
                        "text": answer_text,
                        "full_line": line,
                    }
                )
                continue

            # Continuation of question text
            if current_question and not current_answers:
                current_question["text"] += " " + line

        # Save last question
        if current_question:
            chunk = self._create_exam_chunk(
                question=current_question,
                answers=current_answers,
                document=document,
                doc_id=doc_id,
                chunk_index=chunk_index,
            )
            chunks.append(chunk)

        # Update total_chunks
        for chunk in chunks:
            chunk.total_chunks = len(chunks)

        return chunks

    def _create_exam_chunk(
        self,
        question: Dict,
        answers: List[Dict],
        document: ProcessedDocument,
        doc_id: str,
        chunk_index: int,
    ) -> UniversalChunk:
        """Create chunk for exam question"""

        # Build content
        content_parts = [question["full_line"]]

        # Add question text if not in full_line
        if question["text"] and question["text"] not in question["full_line"]:
            content_parts.append(question["text"])

        # Add answers
        for answer in answers:
            content_parts.append(answer["full_line"])

        content = "\n".join(content_parts)

        # Add context
        section_title = f"Câu {question['number']}"
        enhanced_content = self._add_parent_context(
            chunk_content=content,
            parent_title="Ngân hàng câu hỏi",
            section_title=section_title,
        )

        # Generate chunk ID
        chunk_id = self._generate_chunk_id(
            document_id=doc_id,
            chunk_index=chunk_index,
            level="question",
        )

        # Detect special content
        special_flags = self._detect_special_content(content)

        return UniversalChunk(
            content=enhanced_content,
            chunk_id=chunk_id,
            document_id=doc_id,
            document_type=document.metadata.get("document_type", "exam"),
            hierarchy=[section_title],
            level="question",
            parent_context="Ngân hàng câu hỏi",
            section_title=section_title,
            char_count=len(enhanced_content),
            chunk_index=chunk_index,
            total_chunks=0,  # Updated later
            is_complete_unit=True,  # Question is complete semantic unit
            has_table=special_flags["has_table"],
            has_list=True,  # Questions always have answer list
            extra_metadata={
                "question_number": question["number"],
                "answer_count": len(answers),
            },
        )

    # ============================================================
    # REPORT CHUNKING (PHẦN + Subsection-based)
    # ============================================================

    def _chunk_report(
        self,
        text: str,
        document: ProcessedDocument,
        doc_id: str,
    ) -> List[UniversalChunk]:
        """
        Chunk report documents.

        Strategy:
        - Chunk by PHẦN (Part) or main sections
        - Split large sections by subsections (1.1, 1.2)
        - Preserve complete tables

        Args:
            text: Full report text
            document: ProcessedDocument
            doc_id: Document ID

        Returns:
            List of chunks
        """
        # Parse structure
        structure = self._parse_report_structure(text)

        # Build chunks
        chunks = []
        chunk_index = 0

        for element in structure:
            if element["type"] == "phan":
                # PHẦN-level chunking
                phan_chunks = self._chunk_phan(
                    phan=element,
                    document=document,
                    doc_id=doc_id,
                    chunk_index=chunk_index,
                )
                chunks.extend(phan_chunks)
                chunk_index += len(phan_chunks)

            elif element["type"] == "section":
                # Section-level chunking
                section_chunks = self._chunk_section(
                    section=element,
                    document=document,
                    doc_id=doc_id,
                    chunk_index=chunk_index,
                )
                chunks.extend(section_chunks)
                chunk_index += len(section_chunks)

        # Update total_chunks
        for chunk in chunks:
            chunk.total_chunks = chunk_index

        return chunks

    def _parse_report_structure(self, text: str) -> List[Dict]:
        """
        Parse report structure.

        Identifies:
        - PHẦN (Part)
        - Sections (1., 2., 3.)
        - Subsections (1.1, 1.2, 2.1)
        - Tables

        Returns:
            List of structured elements
        """
        lines = text.split("\n")
        structure = []

        current_phan = None
        current_section = None

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if not line:
                i += 1
                continue

            # Check PHẦN
            phan_match = re.match(self.patterns["phan"], line)
            if phan_match:
                current_phan = {
                    "type": "phan",
                    "number": phan_match.group(2),
                    "title": phan_match.group(3).strip(),
                    "full_title": line,
                    "content_start": i + 1,
                }
                structure.append(current_phan)
                i += 1
                continue

            # Check Section
            section_match = re.match(self.patterns["section"], line)
            if section_match and not re.match(self.patterns["subsection"], line):
                # Finalize previous section
                if current_section:
                    current_section["content_end"] = i

                current_section = {
                    "type": "section",
                    "number": section_match.group(1),
                    "title": section_match.group(2).strip(),
                    "full_title": line,
                    "phan": current_phan["full_title"] if current_phan else None,
                    "content_start": i + 1,
                }
                structure.append(current_section)
                i += 1
                continue

            i += 1

        # Finalize last section
        if current_section:
            current_section["content_end"] = len(lines)

        # Extract content for each element
        for element in structure:
            if "content_start" in element:
                start = element["content_start"]
                end = element.get("content_end", len(lines))
                element["content"] = "\n".join(lines[start:end])

        return structure

    def _chunk_phan(
        self,
        phan: Dict,
        document: ProcessedDocument,
        doc_id: str,
        chunk_index: int,
    ) -> List[UniversalChunk]:
        """Chunk a PHẦN section"""

        content = phan.get("content", "")
        size = len(content)

        # If PHẦN fits in one chunk
        if size <= self.max_size:
            chunk = self._create_report_chunk(
                content=content,
                element=phan,
                document=document,
                doc_id=doc_id,
                chunk_index=chunk_index,
                level="phan",
            )
            return [chunk]

        # Split by subsections or overlap
        return self._split_report_content(
            content=content,
            element=phan,
            document=document,
            doc_id=doc_id,
            chunk_index=chunk_index,
        )

    def _chunk_section(
        self,
        section: Dict,
        document: ProcessedDocument,
        doc_id: str,
        chunk_index: int,
    ) -> List[UniversalChunk]:
        """Chunk a section"""

        content = section.get("content", "")
        size = len(content)

        # If section fits in one chunk
        if size <= self.max_size:
            chunk = self._create_report_chunk(
                content=content,
                element=section,
                document=document,
                doc_id=doc_id,
                chunk_index=chunk_index,
                level="section",
            )
            return [chunk]

        # Split
        return self._split_report_content(
            content=content,
            element=section,
            document=document,
            doc_id=doc_id,
            chunk_index=chunk_index,
        )

    def _split_report_content(
        self,
        content: str,
        element: Dict,
        document: ProcessedDocument,
        doc_id: str,
        chunk_index: int,
    ) -> List[UniversalChunk]:
        """Split report content with overlap"""

        sub_texts = self._split_with_overlap(
            text=content,
            max_size=self.max_size,
            overlap=self.overlap,
        )

        chunks = []
        for idx, sub_text in enumerate(sub_texts):
            chunk = self._create_report_chunk(
                content=sub_text,
                element=element,
                document=document,
                doc_id=doc_id,
                chunk_index=chunk_index + idx,
                level=element["type"],
                is_complete_unit=(len(sub_texts) == 1),
            )
            chunks.append(chunk)

        return chunks

    def _create_report_chunk(
        self,
        content: str,
        element: Dict,
        document: ProcessedDocument,
        doc_id: str,
        chunk_index: int,
        level: str,
        is_complete_unit: bool = True,
    ) -> UniversalChunk:
        """Create chunk for report element"""

        # Build hierarchy
        hierarchy = []
        if element.get("phan"):
            hierarchy.append(element["phan"])
        hierarchy.append(element["full_title"])

        # Parent context
        parent_context = element.get("phan")

        # Add context
        enhanced_content = self._add_parent_context(
            chunk_content=content,
            parent_title=parent_context,
            section_title=element["full_title"],
        )

        # Generate chunk ID
        chunk_id = self._generate_chunk_id(
            document_id=doc_id,
            chunk_index=chunk_index,
            level=level,
        )

        # Detect special content
        special_flags = self._detect_special_content(content)

        return UniversalChunk(
            content=enhanced_content,
            chunk_id=chunk_id,
            document_id=doc_id,
            document_type=document.metadata.get("document_type", "report"),
            hierarchy=hierarchy,
            level=level,
            parent_context=parent_context,
            section_title=element["title"],
            char_count=len(enhanced_content),
            chunk_index=chunk_index,
            total_chunks=0,
            is_complete_unit=is_complete_unit,
            has_table=special_flags["has_table"],
            has_list=special_flags["has_list"],
            extra_metadata={
                "element_number": element["number"],
                "element_type": element["type"],
            },
        )

    # ============================================================
    # BIDDING CHUNKING (Section + Form-based)
    # ============================================================

    def _chunk_bidding(
        self,
        text: str,
        document: ProcessedDocument,
        doc_id: str,
    ) -> List[UniversalChunk]:
        """
        Chunk bidding documents.

        Strategy:
        - Chunk by major sections (I., II., III.)
        - Preserve complete forms (Biểu mẫu, Mẫu số)
        - Preserve complete tables

        Args:
            text: Full bidding text
            document: ProcessedDocument
            doc_id: Document ID

        Returns:
            List of chunks
        """
        # Parse structure
        structure = self._parse_bidding_structure(text)

        # Build chunks
        chunks = []
        chunk_index = 0

        for element in structure:
            if element["type"] == "section":
                section_chunks = self._chunk_bidding_section(
                    section=element,
                    document=document,
                    doc_id=doc_id,
                    chunk_index=chunk_index,
                )
                chunks.extend(section_chunks)
                chunk_index += len(section_chunks)

            elif element["type"] == "form":
                # Forms are usually complete units
                form_chunk = self._create_bidding_chunk(
                    content=element["content"],
                    element=element,
                    document=document,
                    doc_id=doc_id,
                    chunk_index=chunk_index,
                    level="form",
                )
                chunks.append(form_chunk)
                chunk_index += 1

        # Update total_chunks
        for chunk in chunks:
            chunk.total_chunks = chunk_index

        return chunks

    def _parse_bidding_structure(self, text: str) -> List[Dict]:
        """Parse bidding document structure"""

        lines = text.split("\n")
        structure = []

        current_section = None

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if not line:
                i += 1
                continue

            # Check for section
            section_match = re.match(self.patterns["section"], line)
            if section_match:
                # Finalize previous
                if current_section:
                    current_section["content_end"] = i

                current_section = {
                    "type": "section",
                    "number": section_match.group(1),
                    "title": section_match.group(2).strip(),
                    "full_title": line,
                    "content_start": i + 1,
                }
                structure.append(current_section)
                i += 1
                continue

            # Check for form
            form_match = re.match(self.patterns["form"], line)
            if form_match:
                # Forms are separate elements
                form_element = {
                    "type": "form",
                    "prefix": form_match.group(1),
                    "number": form_match.group(2),
                    "title": form_match.group(3).strip(),
                    "full_title": line,
                    "content_start": i + 1,
                }

                # Find form end (next section or form)
                j = i + 1
                while j < len(lines):
                    next_line = lines[j].strip()
                    if re.match(self.patterns["section"], next_line) or re.match(
                        self.patterns["form"], next_line
                    ):
                        break
                    j += 1

                form_element["content_end"] = j
                form_element["content"] = "\n".join(lines[i:j])
                structure.append(form_element)
                i = j
                continue

            i += 1

        # Finalize last section
        if current_section:
            current_section["content_end"] = len(lines)

        # Extract content
        for element in structure:
            if "content_start" in element and "content" not in element:
                start = element["content_start"]
                end = element.get("content_end", len(lines))
                element["content"] = "\n".join(lines[start:end])

        return structure

    def _chunk_bidding_section(
        self,
        section: Dict,
        document: ProcessedDocument,
        doc_id: str,
        chunk_index: int,
    ) -> List[UniversalChunk]:
        """Chunk bidding section"""

        content = section.get("content", "")
        size = len(content)

        # If fits in one chunk
        if size <= self.max_size:
            chunk = self._create_bidding_chunk(
                content=content,
                element=section,
                document=document,
                doc_id=doc_id,
                chunk_index=chunk_index,
                level="section",
            )
            return [chunk]

        # Split with overlap
        sub_texts = self._split_with_overlap(
            text=content,
            max_size=self.max_size,
            overlap=self.overlap,
        )

        chunks = []
        for idx, sub_text in enumerate(sub_texts):
            chunk = self._create_bidding_chunk(
                content=sub_text,
                element=section,
                document=document,
                doc_id=doc_id,
                chunk_index=chunk_index + idx,
                level="section",
                is_complete_unit=(len(sub_texts) == 1),
            )
            chunks.append(chunk)

        return chunks

    def _create_bidding_chunk(
        self,
        content: str,
        element: Dict,
        document: ProcessedDocument,
        doc_id: str,
        chunk_index: int,
        level: str,
        is_complete_unit: bool = True,
    ) -> UniversalChunk:
        """Create chunk for bidding element"""

        # Build hierarchy
        hierarchy = [element["full_title"]]

        # Add context
        enhanced_content = self._add_parent_context(
            chunk_content=content,
            parent_title=None,
            section_title=element["full_title"],
        )

        # Generate chunk ID
        chunk_id = self._generate_chunk_id(
            document_id=doc_id,
            chunk_index=chunk_index,
            level=level,
        )

        # Detect special content
        special_flags = self._detect_special_content(content)

        return UniversalChunk(
            content=enhanced_content,
            chunk_id=chunk_id,
            document_id=doc_id,
            document_type=document.metadata.get("document_type", "bidding"),
            hierarchy=hierarchy,
            level=level,
            parent_context=None,
            section_title=element["title"],
            char_count=len(enhanced_content),
            chunk_index=chunk_index,
            total_chunks=0,
            is_complete_unit=is_complete_unit,
            has_table=special_flags["has_table"],
            has_list=special_flags["has_list"],
            extra_metadata={
                "element_number": element.get("number"),
                "element_type": element["type"],
            },
        )

    def _generate_document_id(self, document: ProcessedDocument) -> str:
        """Generate document ID"""

        doc_type = document.metadata.get("document_type", "unknown")

        # Use title slug
        title = document.metadata.get("title", "untitled")
        title_slug = re.sub(r"[^a-z0-9]+", "_", title.lower())[:50]

        return f"{doc_type}_{title_slug}"
