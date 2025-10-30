"""
Hierarchy Schema Definitions for Vietnamese Legal Documents

This module defines hierarchy field schemas for different types of Vietnamese legal documents.
Each document type has its own hierarchy structure and field naming conventions.
"""

from typing import Dict, List, Optional, Any
from enum import Enum


class DocumentType(Enum):
    """Supported Vietnamese legal document types"""
    LAW = "law"          # Luật
    DECREE = "decree"    # Nghị định  
    CIRCULAR = "circular" # Thông tư
    DECISION = "decision" # Quyết định
    UNKNOWN = "unknown"


class HierarchySchema:
    """Base class for hierarchy schema definitions"""
    
    def __init__(self, doc_type: DocumentType):
        self.doc_type = doc_type
    
    def get_hierarchy_fields(self) -> List[str]:
        """Get list of possible hierarchy field names"""
        raise NotImplementedError
    
    def get_structure_fields(self) -> List[str]:
        """Get list of structure component fields"""
        raise NotImplementedError
    
    def extract_hierarchy_path(self, chunk: Dict[str, Any]) -> Optional[str]:
        """Extract hierarchy path from chunk metadata"""
        raise NotImplementedError
    
    def validate_hierarchy(self, chunks: List[Dict[str, Any]]) -> tuple[int, List[str]]:
        """Validate hierarchy completeness"""
        raise NotImplementedError


class LawHierarchySchema(HierarchySchema):
    """
    Hierarchy schema for Laws (Luật)
    
    Structure: Phần > Chương > Mục > Điều > Khoản > Điểm
    Field name: 'hierarchy'
    Format: "LUẬT > Điều 1 > Khoản 2"
    """
    
    def __init__(self):
        super().__init__(DocumentType.LAW)
    
    def get_hierarchy_fields(self) -> List[str]:
        return ['hierarchy']
    
    def get_structure_fields(self) -> List[str]:
        return ['section', 'chuong', 'dieu', 'khoan', 'parent_dieu']
    
    def extract_hierarchy_path(self, chunk: Dict[str, Any]) -> Optional[str]:
        """Extract hierarchy from law chunk metadata"""
        # Law chunks store hierarchy in metadata sub-dict
        if isinstance(chunk.get('metadata'), dict):
            return chunk['metadata'].get('hierarchy')
        
        # Or directly in chunk
        return chunk.get('hierarchy')
    
    def validate_hierarchy(self, chunks: List[Dict[str, Any]]) -> tuple[int, List[str]]:
        """Validate law hierarchy completeness"""
        issues = []
        chunks_with_hierarchy = 0
        
        for i, chunk in enumerate(chunks):
            hierarchy = self.extract_hierarchy_path(chunk)
            
            if hierarchy and hierarchy.strip():
                chunks_with_hierarchy += 1
                
                # Validate format: should contain "Điều"
                if "Điều" not in hierarchy:
                    issues.append(f"Chunk {i}: Invalid law hierarchy format '{hierarchy}'")
            else:
                issues.append(f"Chunk {i}: Missing hierarchy path")
        
        return chunks_with_hierarchy, issues


class DecreeHierarchySchema(HierarchySchema):
    """
    Hierarchy schema for Decrees (Nghị định)
    
    Structure: Chương > Mục > Điều > Khoản > Điểm  
    Field name: 'hierarchy_path'
    Format: "Chương I > Điều 1 > Khoản 2" (currently empty in test data)
    """
    
    def __init__(self):
        super().__init__(DocumentType.DECREE)
    
    def get_hierarchy_fields(self) -> List[str]:
        return ['hierarchy_path', 'hierarchy']  # Support both for flexibility
    
    def get_structure_fields(self) -> List[str]:
        return ['section_title', 'section_number', 'parent_id', 'parent_type']
    
    def extract_hierarchy_path(self, chunk: Dict[str, Any]) -> Optional[str]:
        """Extract hierarchy from decree chunk"""
        # Try hierarchy_path first (primary)
        hierarchy = chunk.get('hierarchy_path')
        if hierarchy and hierarchy.strip():
            return hierarchy
        
        # Fallback to hierarchy
        hierarchy = chunk.get('hierarchy')
        if hierarchy and hierarchy.strip():
            return hierarchy
        
        # Build from available fields if missing
        return self._build_hierarchy_from_fields(chunk)
    
    def _build_hierarchy_from_fields(self, chunk: Dict[str, Any]) -> Optional[str]:
        """Build hierarchy path from individual fields"""
        parts = []
        
        if section_title := chunk.get('section_title'):
            parts.append(section_title)
        if section_num := chunk.get('section_number'):
            parts.append(f"Mục {section_num}")
        
        # Extract Điều from content if available
        content = chunk.get('content', '')
        if content and 'Điều' in content:
            import re
            dieu_match = re.search(r'Điều\s+(\d+)', content)
            if dieu_match:
                parts.append(f"Điều {dieu_match.group(1)}")
        
        return " > ".join(parts) if parts else None
    
    def validate_hierarchy(self, chunks: List[Dict[str, Any]]) -> tuple[int, List[str]]:
        """Validate decree hierarchy completeness"""
        issues = []
        chunks_with_hierarchy = 0
        
        for i, chunk in enumerate(chunks):
            hierarchy = self.extract_hierarchy_path(chunk)
            
            if hierarchy and hierarchy.strip():
                chunks_with_hierarchy += 1
                
                # Validate format: should contain "Điều" for decrees
                if "Điều" not in hierarchy:
                    issues.append(f"Chunk {i}: Weak decree hierarchy '{hierarchy}' (no Điều reference)")
            else:
                # For decrees, missing hierarchy is more acceptable since structure varies
                pass
        
        return chunks_with_hierarchy, issues


class HierarchySchemaFactory:
    """Factory for creating appropriate hierarchy schema based on document type"""
    
    _schemas = {
        DocumentType.LAW: LawHierarchySchema,
        DocumentType.DECREE: DecreeHierarchySchema,
    }
    
    @classmethod
    def create_schema(cls, doc_type: str) -> HierarchySchema:
        """Create hierarchy schema for document type"""
        # Normalize doc_type
        doc_type_lower = doc_type.lower().strip()
        
        # Map common variations
        if doc_type_lower in ['law', 'luật', 'luat']:
            enum_type = DocumentType.LAW
        elif doc_type_lower in ['decree', 'nghị định', 'nghi dinh', 'nd']:
            enum_type = DocumentType.DECREE
        elif doc_type_lower in ['circular', 'thông tư', 'thong tu', 'tt']:
            enum_type = DocumentType.CIRCULAR
        elif doc_type_lower in ['decision', 'quyết định', 'quyet dinh', 'qd']:
            enum_type = DocumentType.DECISION
        else:
            enum_type = DocumentType.UNKNOWN
        
        # Get schema class
        schema_class = cls._schemas.get(enum_type)
        if not schema_class:
            # Fallback to law schema for unknown types
            schema_class = LawHierarchySchema
        
        return schema_class()
    
    @classmethod
    def detect_document_type(cls, chunk: Dict[str, Any]) -> DocumentType:
        """Auto-detect document type from chunk metadata"""
        # Check explicit doc_type field
        if doc_type := chunk.get('doc_type'):
            if doc_type == 'decree':
                return DocumentType.DECREE
            elif doc_type == 'law':
                return DocumentType.LAW
        
        # Check metadata sub-dict
        if isinstance(chunk.get('metadata'), dict):
            metadata = chunk['metadata']
            if source := metadata.get('source_file', ''):
                if 'ND' in source or 'Nghi dinh' in source:
                    return DocumentType.DECREE
                elif 'Luat' in source or 'Law' in source:
                    return DocumentType.LAW
        
        # Check content patterns
        content = chunk.get('content', '') or chunk.get('text', '')
        if content:
            if 'Nghị định' in content:
                return DocumentType.DECREE
            elif 'Luật' in content:
                return DocumentType.LAW
        
        return DocumentType.UNKNOWN


# Convenience functions for backward compatibility
def get_hierarchy_path(chunk: Dict[str, Any]) -> Optional[str]:
    """Get hierarchy path from chunk using appropriate schema"""
    doc_type = HierarchySchemaFactory.detect_document_type(chunk)
    schema = HierarchySchemaFactory.create_schema(doc_type.value)
    return schema.extract_hierarchy_path(chunk)


def validate_hierarchy_completeness(chunks: List[Dict[str, Any]], 
                                   doc_type: Optional[str] = None) -> tuple[int, List[str]]:
    """Validate hierarchy completeness for chunks"""
    if not chunks:
        return 0, []
    
    # Auto-detect if not provided
    if not doc_type:
        detected_type = HierarchySchemaFactory.detect_document_type(chunks[0])
        doc_type = detected_type.value
    
    schema = HierarchySchemaFactory.create_schema(doc_type)
    return schema.validate_hierarchy(chunks)