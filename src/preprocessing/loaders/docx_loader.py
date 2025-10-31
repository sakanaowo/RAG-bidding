"""
DOCX Loader for Vietnamese Legal Documents
Refactored from archive/preprocessing_v1/law_preprocessing/extractors/docx_extractor.py
Integrated with V2 Unified Schema
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional, TYPE_CHECKING
from dataclasses import dataclass
from datetime import datetime

if TYPE_CHECKING:
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    from docx.oxml.text.paragraph import CT_P
    from docx.oxml.table import CT_Tbl

try:
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    from docx.oxml.text.paragraph import CT_P
    from docx.oxml.table import CT_Tbl
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


@dataclass
class RawDocxContent:
    """
    Raw content extracted from DOCX file.
    This is pre-schema, will be converted to DocumentInfo later.
    """
    text: str
    metadata: Dict
    structure: List[Dict]  # Hierarchical elements detected
    tables: List[Dict]  # Extracted tables
    statistics: Dict


class DocxLoader:
    """
    Load and extract content from DOCX files for Vietnamese legal documents.
    
    Supports:
    - Law (Luật)
    - Decree (Nghị định)
    - Circular (Thông tư)
    - Decision (Quyết định)
    - Bidding documents
    
    Compatible with UnifiedLegalChunk schema.
    """
    
    def __init__(self, preserve_formatting: bool = False):
        """
        Args:
            preserve_formatting: Whether to preserve text formatting (bold, italic)
        """
        if not DOCX_AVAILABLE:
            raise ImportError(
                "python-docx is required. Install with: pip install python-docx"
            )
        
        self.preserve_formatting = preserve_formatting
        
        # Regex patterns for Vietnamese legal document structure
        self.patterns = {
            "phan": r"^(PHẦN THỨ|Phần\s+[IVXLCDM]+|PHẦN\s+[IVXLCDM]+)[:\s.]",
            "chuong": r"^(CHƯƠNG|Chương)\s+([IVXLCDM]+|[0-9]+)[:\s.]",
            "muc": r"^(MỤC|Mục)\s+(\d+)[:\s.]",
            "dieu": r"^Điều\s+(\d+[a-z]?)[:\s.]",
            "khoan": r"^\d+\.\s+",
            "diem": r"^[a-zđ]\)\s+",
        }
    
    def load(self, file_path: str | Path) -> RawDocxContent:
        """
        Load DOCX file and extract raw content.
        
        Args:
            file_path: Path to .docx file
            
        Returns:
            RawDocxContent with extracted text, metadata, structure
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not file_path.suffix.lower() == '.docx':
            raise ValueError(f"Not a DOCX file: {file_path}")
        
        # Load document
        doc = Document(file_path)
        
        # Extract components
        metadata = self._extract_metadata(doc, file_path)
        text, structure = self._extract_text_and_structure(doc)
        tables = self._extract_tables(doc)
        statistics = self._calculate_statistics(text, structure, tables)
        
        return RawDocxContent(
            text=text,
            metadata=metadata,
            structure=structure,
            tables=tables,
            statistics=statistics,
        )
    
    def _extract_metadata(self, doc: Document, file_path: Path) -> Dict:
        """Extract metadata from document properties"""
        core_props = doc.core_properties
        
        metadata = {
            "filename": file_path.name,
            "file_path": str(file_path.absolute()),
            "title": core_props.title or file_path.stem,
            "author": core_props.author or "",
            "subject": core_props.subject or "",
            "created": core_props.created.isoformat() if core_props.created else None,
            "modified": core_props.modified.isoformat() if core_props.modified else None,
        }
        
        # Parse Vietnamese legal document info from title
        doc_info = self._parse_document_info(metadata["title"])
        metadata.update(doc_info)
        
        return metadata
    
    def _parse_document_info(self, title: str) -> Dict:
        """
        Parse Vietnamese legal document information from title.
        
        Patterns:
        - Luật số 43/2013-QH13
        - Nghị định số 63/2014-NĐ-CP
        - Thông tư số 05/2015-TT-BXD
        - Quyết định số 123/2020-QĐ-BYT
        """
        info = {
            "doc_type_detected": "unknown",
            "doc_number": "",
            "doc_year": "",
            "authority_code": "",
        }
        
        # Law (Luật)
        law_match = re.search(r"Luật\s+(?:số\s+)?(\d+)/(\d{4})-?(QH\d+)?", title, re.I)
        if law_match:
            info["doc_type_detected"] = "law"
            info["doc_number"] = f"{law_match.group(1)}/{law_match.group(2)}"
            info["doc_year"] = law_match.group(2)
            if law_match.group(3):
                info["authority_code"] = law_match.group(3)
                info["doc_number"] += f"-{law_match.group(3)}"
        
        # Decree (Nghị định)
        decree_match = re.search(
            r"Nghị định\s+(?:số\s+)?(\d+)/(\d{4})-?(NĐ-CP|ND-CP)?", title, re.I
        )
        if decree_match:
            info["doc_type_detected"] = "decree"
            info["doc_number"] = f"{decree_match.group(1)}/{decree_match.group(2)}"
            info["doc_year"] = decree_match.group(2)
            if decree_match.group(3):
                info["authority_code"] = decree_match.group(3).upper()
                info["doc_number"] += f"-{info['authority_code']}"
        
        # Circular (Thông tư)
        circular_match = re.search(
            r"Thông tư\s+(?:số\s+)?(\d+)/(\d{4})-?(TT-[\w]+)?", title, re.I
        )
        if circular_match:
            info["doc_type_detected"] = "circular"
            info["doc_number"] = f"{circular_match.group(1)}/{circular_match.group(2)}"
            info["doc_year"] = circular_match.group(2)
            if circular_match.group(3):
                info["authority_code"] = circular_match.group(3).upper()
                info["doc_number"] += f"-{info['authority_code']}"
        
        # Decision (Quyết định)
        decision_match = re.search(
            r"Quyết định\s+(?:số\s+)?(\d+)/(\d{4})-?(QĐ-[\w]+)?", title, re.I
        )
        if decision_match:
            info["doc_type_detected"] = "decision"
            info["doc_number"] = f"{decision_match.group(1)}/{decision_match.group(2)}"
            info["doc_year"] = decision_match.group(2)
            if decision_match.group(3):
                info["authority_code"] = decision_match.group(3).upper()
                info["doc_number"] += f"-{info['authority_code']}"
        
        return info
    
    def _extract_text_and_structure(self, doc: Document) -> Tuple[str, List[Dict]]:
        """
        Extract text and detect hierarchical structure.
        
        Returns:
            (full_text, structure_list)
        """
        full_text = []
        structure = []
        current_hierarchy = {
            "phan": None,
            "chuong": None,
            "muc": None,
            "dieu": None,
        }
        
        for element in doc.element.body:
            if isinstance(element, CT_P):
                # Paragraph
                para = Paragraph(element, doc)
                text = para.text.strip()
                
                if not text:
                    continue
                
                # Detect structural elements
                struct_info = self._detect_structure(text, current_hierarchy)
                
                if struct_info:
                    structure.append(struct_info)
                    # Update current hierarchy
                    for key in ["phan", "chuong", "muc", "dieu"]:
                        if key in struct_info:
                            current_hierarchy[key] = struct_info[key]
                
                full_text.append(text)
            
            elif isinstance(element, CT_Tbl):
                # Table - mark position for later processing
                full_text.append("[TABLE_PLACEHOLDER]")
        
        return "\n".join(full_text), structure
    
    def _detect_structure(self, text: str, current_hierarchy: Dict) -> Optional[Dict]:
        """
        Detect if text is a structural element (Phần, Chương, Mục, Điều).
        
        Returns:
            Dict with structure info or None
        """
        # Check Phần
        phan_match = re.match(self.patterns["phan"], text)
        if phan_match:
            return {
                "type": "phan",
                "text": text,
                "phan": self._extract_roman_or_number(text),
            }
        
        # Check Chương
        chuong_match = re.match(self.patterns["chuong"], text)
        if chuong_match:
            return {
                "type": "chuong",
                "text": text,
                "phan": current_hierarchy.get("phan"),
                "chuong": chuong_match.group(2),
            }
        
        # Check Mục
        muc_match = re.match(self.patterns["muc"], text)
        if muc_match:
            return {
                "type": "muc",
                "text": text,
                "phan": current_hierarchy.get("phan"),
                "chuong": current_hierarchy.get("chuong"),
                "muc": muc_match.group(2),
            }
        
        # Check Điều
        dieu_match = re.match(self.patterns["dieu"], text)
        if dieu_match:
            return {
                "type": "dieu",
                "text": text,
                "phan": current_hierarchy.get("phan"),
                "chuong": current_hierarchy.get("chuong"),
                "muc": current_hierarchy.get("muc"),
                "dieu": dieu_match.group(1),
            }
        
        return None
    
    def _extract_roman_or_number(self, text: str) -> Optional[str]:
        """Extract Roman numeral or number from Phần text"""
        match = re.search(r"[IVXLCDM]+|\d+", text)
        return match.group(0) if match else None
    
    def _extract_tables(self, doc: Document) -> List[Dict]:
        """Extract all tables from document"""
        tables = []
        
        for table_idx, table in enumerate(doc.tables):
            table_data = {
                "table_id": f"table_{table_idx}",
                "rows": len(table.rows),
                "cols": len(table.columns),
                "data": [],
            }
            
            # Extract table content
            for row in table.rows:
                row_data = [cell.text.strip() for cell in row.cells]
                table_data["data"].append(row_data)
            
            tables.append(table_data)
        
        return tables
    
    def _calculate_statistics(
        self, text: str, structure: List[Dict], tables: List[Dict]
    ) -> Dict:
        """Calculate statistics about extracted content"""
        # Count structural elements
        structure_counts = {}
        for struct in structure:
            struct_type = struct.get("type", "unknown")
            structure_counts[struct_type] = structure_counts.get(struct_type, 0) + 1
        
        return {
            "char_count": len(text),
            "word_count": len(text.split()),
            "line_count": text.count("\n") + 1,
            "table_count": len(tables),
            "dieu_count": structure_counts.get("dieu", 0),
            "chuong_count": structure_counts.get("chuong", 0),
            "phan_count": structure_counts.get("phan", 0),
            "muc_count": structure_counts.get("muc", 0),
        }
