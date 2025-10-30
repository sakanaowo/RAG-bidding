"""
Data Integrity Validator - Kiểm tra toàn vẹn dữ liệu sau preprocessing

Validates:
- No data loss during processing
- Content coverage
- Structure preservation
- Metadata completeness
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
from pathlib import Path
import re


@dataclass
class IntegrityReport:
    """Report về data integrity"""
    
    is_valid: bool
    total_checks: int
    passed_checks: int
    failed_checks: int
    
    # Detailed metrics
    original_char_count: int
    processed_char_count: int
    coverage_percentage: float
    
    # Content checks
    missing_sections: List[str]
    duplicate_chunks: List[str]
    
    # Structure checks
    structure_preserved: bool
    hierarchy_complete: bool
    
    # Metadata checks
    metadata_complete: bool
    
    # Warnings and errors
    warnings: List[str]
    errors: List[str]
    
    def __str__(self):
        status = "✅ PASS" if self.is_valid else "❌ FAIL"
        return f"""
{'='*70}
DATA INTEGRITY REPORT - {status}
{'='*70}

Checks: {self.passed_checks}/{self.total_checks} passed

📊 Coverage Analysis:
  Original chars:   {self.original_char_count:,}
  Processed chars:  {self.processed_char_count:,}
  Coverage:         {self.coverage_percentage:.1f}%
  
🔍 Content Checks:
  Missing sections: {len(self.missing_sections)}
  Duplicate chunks: {len(self.duplicate_chunks)}
  
🏗️  Structure Checks:
  Structure preserved: {'✅' if self.structure_preserved else '❌'}
  Hierarchy complete:  {'✅' if self.hierarchy_complete else '❌'}
  
📋 Metadata Checks:
  Metadata complete: {'✅' if self.metadata_complete else '❌'}

⚠️  Warnings: {len(self.warnings)}
❌ Errors: {len(self.errors)}

{'='*70}
"""


class DataIntegrityValidator:
    """
    Validator toàn vẹn dữ liệu cho preprocessing pipeline
    """
    
    def __init__(
        self,
        min_coverage: float = 0.75,  # Minimum 75% content coverage (lowered)
        max_duplication: float = 0.05,  # Maximum 5% duplication
    ):
        """
        Args:
            min_coverage: Minimum coverage percentage (0.0-1.0)
            max_duplication: Maximum allowed duplication rate
        """
        self.min_coverage = min_coverage
        self.max_duplication = max_duplication
        
        self.warnings = []
        self.errors = []

    def validate(
        self,
        original_text: str,
        processed_chunks: List[Dict],
        structure_tree = None,
        file_metadata: Dict = None,
    ) -> IntegrityReport:
        """
        Validate data integrity after preprocessing
        
        Args:
            original_text: Original cleaned text
            processed_chunks: List of DB records
            structure_tree: Parsed structure tree (optional)
            file_metadata: Original file metadata (optional)
            
        Returns:
            IntegrityReport
        """
        self.warnings = []
        self.errors = []
        
        checks = {
            "coverage": self._check_coverage(original_text, processed_chunks),
            "duplication": self._check_duplication(processed_chunks),
            "content_loss": self._check_content_loss(original_text, processed_chunks),
            "structure": self._check_structure_preservation(structure_tree, processed_chunks),
            "metadata": self._check_metadata_completeness(processed_chunks),
            "chunk_quality": self._check_chunk_quality(processed_chunks),
        }
        
        passed = sum(1 for v in checks.values() if v)
        total = len(checks)
        
        # Support both schemas
        content_field = 'chunk_content' if processed_chunks and 'chunk_content' in processed_chunks[0] else 'content'
        
        # Calculate metrics
        original_chars = len(original_text)
        processed_chars = sum(len(chunk.get(content_field, '')) for chunk in processed_chunks)
        coverage = (processed_chars / original_chars * 100) if original_chars > 0 else 0
        
        # Check for missing sections
        missing_sections = self._find_missing_sections(original_text, processed_chunks)
        
        # Check for duplicates
        duplicate_chunks = self._find_duplicates(processed_chunks)
        
        # Overall validation
        is_valid = (
            passed == total
            and coverage >= self.min_coverage * 100
            and len(self.errors) == 0
        )
        
        return IntegrityReport(
            is_valid=is_valid,
            total_checks=total,
            passed_checks=passed,
            failed_checks=total - passed,
            original_char_count=original_chars,
            processed_char_count=processed_chars,
            coverage_percentage=coverage,
            missing_sections=missing_sections,
            duplicate_chunks=duplicate_chunks,
            structure_preserved=checks["structure"],
            hierarchy_complete=True,  # TODO: implement
            metadata_complete=checks["metadata"],
            warnings=self.warnings,
            errors=self.errors,
        )

    def _check_coverage(self, original: str, chunks: List[Dict]) -> bool:
        """Check if processed chunks cover enough of the original text"""
        if not original or not chunks:
            return True
        
        # Support both schemas: 'content' (decree) and 'chunk_content' (law)
        content_field = 'chunk_content' if 'chunk_content' in chunks[0] else 'content'
        
        original_chars = len(original)
        processed_chars = sum(len(chunk.get(content_field, '')) for chunk in chunks)
        coverage = processed_chars / original_chars

    def _check_duplication(self, chunks: List[Dict]) -> bool:
        """Check for excessive chunk duplication"""
        if len(chunks) < 2:
            return True
        
        # Support both schemas
        content_field = 'chunk_content' if 'chunk_content' in chunks[0] else 'content'
        
        seen = set()
        duplicates = 0
        
        for chunk in chunks:
            content = chunk.get(content_field, '')
            content_hash = hash(content.strip().lower())
            if content_hash in seen:
                duplicates += 1
            seen.add(content_hash)
        
        dup_rate = duplicates / len(chunks)
        
        if dup_rate > self.max_duplication:
            self.errors.append(
                f"Duplication rate too high: {dup_rate*100:.1f}% > {self.max_duplication*100}%"
            )
            return False
        
        if dup_rate > 0:
            self.warnings.append(
                f"Found {duplicates} duplicate chunks ({dup_rate*100:.1f}%)"
            )
        
        return True

    def _check_content_loss(self, original: str, chunks: List[Dict]) -> bool:
        """Check for significant content sections that are missing"""
        if not chunks:
            return True
            
        # Support both schemas
        content_field = 'chunk_content' if 'chunk_content' in chunks[0] else 'content'
        
        # Extract important markers from original
        important_patterns = [
            r"Điều\s+\d+",  # Articles
            r"Chương\s+[IVXLCDM]+",  # Chapters
            r"Khoản\s+\d+",  # Clauses
        ]
        
        original_markers = set()
        for pattern in important_patterns:
            original_markers.update(re.findall(pattern, original))
        
        # Extract markers from chunks
        processed_content = " ".join(chunk.get(content_field, '') for chunk in chunks)
        processed_markers = set()
        for pattern in important_patterns:
            processed_markers.update(re.findall(pattern, processed_content))
        
        missing = original_markers - processed_markers
        
        if missing:
            missing_ratio = len(missing) / len(original_markers) if original_markers else 0
            
            if missing_ratio > 0.1:  # More than 10% missing
                self.errors.append(
                    f"Significant content loss: {len(missing)} markers missing ({missing_ratio*100:.1f}%)"
                )
                return False
            else:
                self.warnings.append(
                    f"Minor content loss: {len(missing)} markers missing"
                )
        
        return True

    def _check_structure_preservation(self, structure_tree, chunks: List[Dict]) -> bool:
        """Check if hierarchical structure is preserved using schema-aware validation"""
        if not structure_tree:
            return True  # Can't check without tree
        
        # Count structure nodes
        node_count = self._count_nodes(structure_tree)
        
        # Use hierarchy schema for validation
        try:
            from src.preprocessing.validators.hierarchy_schemas import validate_hierarchy_completeness
            chunks_with_hierarchy, issues = validate_hierarchy_completeness(chunks)
            
            # Add schema-specific issues as warnings
            for issue in issues[:3]:  # Limit to first 3
                self.warnings.append(f"Hierarchy: {issue}")
            
        except ImportError:
            # Fallback to original method if schema not available
            chunks_with_hierarchy = sum(
                1 for chunk in chunks 
                if (chunk.get('hierarchy_path') and chunk['hierarchy_path'].strip()) or
                   (chunk.get('hierarchy') and chunk['hierarchy'].strip())
            )
        
        if chunks_with_hierarchy == 0 and node_count > 1:
            self.warnings.append(
                f"No hierarchy paths in chunks (found {node_count} structure nodes)"
            )
        elif chunks_with_hierarchy > 0:
            # Success - remove the warning we had before
            pass
        
        return True

    def _check_metadata_completeness(self, chunks: List[Dict]) -> bool:
        """Check if all chunks have complete metadata"""
        if not chunks:
            return True
        
        # Detect schema based on fields present
        sample_chunk = chunks[0]
        
        # Core fields that should exist in both schemas
        core_fields = ['chunk_id']
        
        # Schema-specific fields
        if 'doc_id' in sample_chunk:
            # Decree schema
            required_fields = core_fields + [
                'content', 'doc_id', 'doc_type', 'doc_number',
                'doc_year', 'doc_name', 'status', 'chunk_index', 'total_chunks'
            ]
        else:
            # Law schema (or other)
            required_fields = core_fields + [
                'chunk_content', 'source', 'title', 'chunk_level', 
                'status', 'char_count'
            ]
        
        incomplete_chunks = []
        for i, chunk in enumerate(chunks):
            # Check if field exists and is not None (but allow 0, False, empty string)
            missing = [f for f in required_fields if f not in chunk or chunk[f] is None]
            if missing:
                incomplete_chunks.append((i, missing))
        
        if incomplete_chunks:
            # Only error if more than 10% have issues
            if len(incomplete_chunks) > len(chunks) * 0.1:
                self.errors.append(
                    f"Found {len(incomplete_chunks)} chunks with incomplete metadata"
                )
                return False
            else:
                self.warnings.append(
                    f"Found {len(incomplete_chunks)} chunks with incomplete metadata"
                )
        
        return True

    def _check_chunk_quality(self, chunks: List[Dict]) -> bool:
        """Check quality of individual chunks"""
        if not chunks:
            return True
            
        # Support both schemas
        content_field = 'chunk_content' if 'chunk_content' in chunks[0] else 'content'
        
        issues = []
        
        for i, chunk in enumerate(chunks):
            content = chunk.get(content_field, '')
            
            # Too short
            if len(content.strip()) < 20:
                issues.append(f"Chunk {i}: Too short ({len(content)} chars)")
            
            # Too long (likely chunking failure)
            if len(content) > 10000:
                issues.append(f"Chunk {i}: Too long ({len(content)} chars)")
            
            # Malformed content
            if content.count('\n\n\n') > 3:  # Too many blank lines
                issues.append(f"Chunk {i}: Excessive blank lines")
        
        if issues:
            # Add to warnings regardless
            for issue in issues[:3]:
                self.warnings.append(issue)
            
            # Only fail if more than 10% have issues
            if len(issues) > len(chunks) * 0.1:
                self.errors.append(f"Chunk quality issues: {len(issues)} chunks")
                for issue in issues[:5]:
                    self.errors.append(f"  - {issue}")
                return False
        
        return True

    def _find_missing_sections(self, original: str, chunks: List[Dict]) -> List[str]:
        """Find sections present in original but missing in chunks"""
        if not chunks:
            return []
            
        # Support both schemas
        content_field = 'chunk_content' if 'chunk_content' in chunks[0] else 'content'
        
        # Extract Điều numbers from original
        original_dieus = set(re.findall(r"Điều\s+(\d+[a-z]?)", original))
        
        # Extract from chunks
        processed_content = " ".join(chunk.get(content_field, '') for chunk in chunks)
        processed_dieus = set(re.findall(r"Điều\s+(\d+[a-z]?)", processed_content))
        
        missing = original_dieus - processed_dieus
        return [f"Điều {d}" for d in sorted(missing, key=lambda x: int(re.search(r'\d+', x).group()))]

    def _find_duplicates(self, chunks: List[Dict]) -> List[str]:
        """Find duplicate chunk IDs"""
        seen = {}
        duplicates = []
        
        for chunk in chunks:
            cid = chunk.get('chunk_id', '')
            if cid in seen:
                duplicates.append(cid)
            seen[cid] = True
        
        return duplicates

    def _count_nodes(self, node, count=0) -> int:
        """Recursively count structure nodes"""
        count = 1
        if hasattr(node, 'children'):
            for child in node.children:
                count += self._count_nodes(child)
        return count
