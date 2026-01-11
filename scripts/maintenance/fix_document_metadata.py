#!/usr/bin/env python3
"""
Fix Document Metadata - Data Quality Improvement Script

This script analyzes and fixes data quality issues in the documents table:
1. document_id: Fix "untitled" patterns
2. document_name: Extract meaningful names from content/filename
3. filename: Restore original filenames
4. filepath/source_file: Populate from available sources
5. document_type: Fix file extension as type (pdf/txt/docx → proper types)
6. category: Update category mapping

Usage:
    # Analyze only (dry run)
    python scripts/maintenance/fix_document_metadata.py --analyze
    
    # Fix with confirmation
    python scripts/maintenance/fix_document_metadata.py --fix
    
    # Fix specific issues
    python scripts/maintenance/fix_document_metadata.py --fix --issues document_type,category

Author: RAG Bidding Team
Date: 2026-01-11
"""

import sys
import re
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text, update
from sqlalchemy.orm import Session

from src.models.base import SessionLocal
from src.models.documents import Document
from src.models.document_chunks import DocumentChunk

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Correct category mapping
CATEGORY_MAP = {
    "law": "Luật chính",
    "decree": "Nghị định",
    "circular": "Thông tư",
    "decision": "Quyết định",
    "bidding": "Mẫu biểu đấu thầu",
    "template": "Mẫu báo cáo",
    "exam": "Câu hỏi thi",
    "guidance": "Hướng dẫn",
    "other": "Khác",
}

# File extensions that were incorrectly used as document_type
FILE_EXTENSIONS_AS_TYPE = {"pdf", "txt", "docx", "doc", "xlsx", "xls"}

# Patterns to identify document types from filename
DOC_TYPE_PATTERNS = {
    "law": [
        r"[Ll]uật",
        r"[Ll]aw",
    ],
    "decree": [
        r"[Nn]ghị\s*định",
        r"[Dd]ecree",
        r"[Nn]D[-_]?\d+",
    ],
    "circular": [
        r"[Tt]hông\s*tư",
        r"[Cc]ircular",
        r"[Tt]T[-_]?\d+",
    ],
    "decision": [
        r"[Qq]uyết\s*định",
        r"[Dd]ecision",
        r"[Qq]Đ[-_]?\d+",
    ],
    "bidding": [
        r"[Mm]ẫu\s+số",
        r"[Mm]ẫu\s+HSMT",
        r"[Pp]hụ\s+lục",
        r"[Bb]iểu\s+mẫu",
        r"HSYC",
        r"BCĐG",
        r"[Đđ]ấu\s*thầu",
        r"[Tt]ender",
        r"[Bb]idding",
    ],
    "template": [
        r"[Bb]iểu\s+mẫu\s+báo\s+cáo",
        r"[Mm]ẫu\s+BC",
        r"[Tt]emplate",
    ],
    "exam": [
        r"[Cc]âu\s+hỏi",
        r"[Nn]gân\s+hàng\s+câu\s+hỏi",
        r"[Ee]xam",
        r"[Qq]uiz",
    ],
}


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

def analyze_documents(db: Session) -> Dict[str, Any]:
    """
    Analyze documents table for data quality issues.
    
    Returns:
        Dictionary with analysis results
    """
    logger.info("="*60)
    logger.info("ANALYZING DOCUMENT DATA QUALITY")
    logger.info("="*60)
    
    results = {
        "total_documents": 0,
        "issues": {
            "document_id": [],
            "document_name": [],
            "filename": [],
            "source_file": [],
            "filepath": [],
            "document_type": [],
            "category": [],
        },
        "summary": {},
    }
    
    # Get all documents
    documents = db.query(Document).all()
    results["total_documents"] = len(documents)
    
    logger.info(f"\nTotal documents: {len(documents)}")
    
    for doc in documents:
        # Check document_id issues
        if doc.document_id and "_untitled_" in doc.document_id:
            results["issues"]["document_id"].append({
                "id": str(doc.id),
                "current": doc.document_id,
                "problem": "Contains '_untitled_' pattern",
            })
        
        # Check document_name issues
        if doc.document_name:
            if doc.document_name.startswith(("Bidding Untitled", "Circular Untitled", "Law Untitled", "Decree Untitled")):
                results["issues"]["document_name"].append({
                    "id": str(doc.id),
                    "current": doc.document_name,
                    "problem": "Generated from document_id, not meaningful",
                })
        
        # Check filename issues
        if doc.filename:
            if "_untitled_" in doc.filename or doc.filename.startswith(("bidding_", "circular_", "law_", "decree_")):
                results["issues"]["filename"].append({
                    "id": str(doc.id),
                    "current": doc.filename,
                    "problem": "Generated filename, not original",
                })
        
        # Check source_file issues
        if doc.source_file is None or doc.source_file == "None":
            results["issues"]["source_file"].append({
                "id": str(doc.id),
                "current": str(doc.source_file),
                "problem": "NULL or 'None' value",
            })
        
        # Check filepath issues
        if doc.filepath is None:
            results["issues"]["filepath"].append({
                "id": str(doc.id),
                "current": None,
                "problem": "NULL value",
            })
        
        # Check document_type issues (file extension as type)
        if doc.document_type and doc.document_type.lower() in FILE_EXTENSIONS_AS_TYPE:
            results["issues"]["document_type"].append({
                "id": str(doc.id),
                "current": doc.document_type,
                "problem": f"File extension '{doc.document_type}' used as document_type",
            })
        
        # Check category issues
        if doc.document_type == "bidding" and doc.category == "Khác":
            results["issues"]["category"].append({
                "id": str(doc.id),
                "current": doc.category,
                "document_type": doc.document_type,
                "problem": "Bidding document categorized as 'Khác'",
            })
    
    # Summary
    results["summary"] = {
        "document_id_issues": len(results["issues"]["document_id"]),
        "document_name_issues": len(results["issues"]["document_name"]),
        "filename_issues": len(results["issues"]["filename"]),
        "source_file_issues": len(results["issues"]["source_file"]),
        "filepath_issues": len(results["issues"]["filepath"]),
        "document_type_issues": len(results["issues"]["document_type"]),
        "category_issues": len(results["issues"]["category"]),
    }
    
    # Print summary
    logger.info("\n" + "="*60)
    logger.info("ISSUE SUMMARY")
    logger.info("="*60)
    
    for issue_type, count in results["summary"].items():
        pct = count * 100 / results["total_documents"] if results["total_documents"] > 0 else 0
        status = "❌" if pct > 50 else "⚠️" if pct > 10 else "✅"
        logger.info(f"  {status} {issue_type}: {count} ({pct:.1f}%)")
    
    return results


def infer_document_type(filename: str, document_name: str = None, content: str = None) -> Optional[str]:
    """
    Infer document type from filename, name, or content.
    
    Args:
        filename: Original filename
        document_name: Document name
        content: First chunk content (optional)
    
    Returns:
        Inferred document type or None
    """
    # Check against patterns
    text_to_check = f"{filename or ''} {document_name or ''}"
    
    for doc_type, patterns in DOC_TYPE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_to_check, re.IGNORECASE):
                return doc_type
    
    return None


def extract_document_name_from_content(content: str) -> Optional[str]:
    """
    Extract document name from content (usually first meaningful line).
    
    Args:
        content: Document content
    
    Returns:
        Extracted document name or None
    """
    if not content:
        return None
    
    # Split into lines and find first meaningful line
    lines = content.strip().split('\n')
    
    for line in lines[:10]:  # Check first 10 lines
        line = line.strip()
        
        # Skip section markers
        if line.startswith('[') and line.endswith(']'):
            continue
        
        # Skip empty lines
        if not line or len(line) < 5:
            continue
        
        # Skip lines that are just numbers or punctuation
        if re.match(r'^[\d\s\.\-\:]+$', line):
            continue
        
        # Found a meaningful line
        # Clean it up
        clean_name = re.sub(r'\s+', ' ', line)
        
        # Limit length
        if len(clean_name) > 200:
            clean_name = clean_name[:200] + "..."
        
        return clean_name
    
    return None


# =============================================================================
# FIX FUNCTIONS
# =============================================================================

def fix_document_type_issues(db: Session, dry_run: bool = True) -> int:
    """
    Fix documents where file extension was used as document_type.
    
    Args:
        db: Database session
        dry_run: If True, don't commit changes
    
    Returns:
        Number of documents fixed
    """
    logger.info("\n" + "-"*40)
    logger.info("Fixing document_type issues...")
    logger.info("-"*40)
    
    fixed_count = 0
    
    # Get documents with file extension as type
    docs = db.query(Document).filter(
        Document.document_type.in_(list(FILE_EXTENSIONS_AS_TYPE))
    ).all()
    
    for doc in docs:
        # Try to infer correct type
        inferred_type = infer_document_type(
            filename=doc.filename or "",
            document_name=doc.document_name or "",
        )
        
        if not inferred_type:
            # Check content from first chunk
            first_chunk = db.query(DocumentChunk).filter(
                DocumentChunk.document_id == doc.id,
                DocumentChunk.chunk_index == 0
            ).first()
            
            if first_chunk:
                inferred_type = infer_document_type(
                    filename=doc.filename or "",
                    document_name=doc.document_name or "",
                    content=first_chunk.content[:500]
                )
        
        if inferred_type:
            old_type = doc.document_type
            new_type = inferred_type
            
            logger.info(f"  {doc.id}: {old_type} → {new_type}")
            
            if not dry_run:
                doc.document_type = new_type
                fixed_count += 1
        else:
            logger.warning(f"  {doc.id}: Could not infer type (keeping '{doc.document_type}')")
    
    if not dry_run:
        db.commit()
    
    logger.info(f"  Fixed {fixed_count} documents")
    return fixed_count


def fix_category_issues(db: Session, dry_run: bool = True) -> int:
    """
    Fix category based on document_type.
    
    Args:
        db: Database session
        dry_run: If True, don't commit changes
    
    Returns:
        Number of documents fixed
    """
    logger.info("\n" + "-"*40)
    logger.info("Fixing category issues...")
    logger.info("-"*40)
    
    fixed_count = 0
    
    # Get all documents and check category matches type
    docs = db.query(Document).all()
    
    for doc in docs:
        if doc.document_type:
            expected_category = CATEGORY_MAP.get(doc.document_type, "Khác")
            
            if doc.category != expected_category:
                old_cat = doc.category
                new_cat = expected_category
                
                logger.info(f"  {doc.id}: '{old_cat}' → '{new_cat}' (type={doc.document_type})")
                
                if not dry_run:
                    doc.category = new_cat
                    fixed_count += 1
    
    if not dry_run:
        db.commit()
    
    logger.info(f"  Fixed {fixed_count} documents")
    return fixed_count


def fix_source_file_issues(db: Session, dry_run: bool = True) -> int:
    """
    Fix source_file NULL issues where possible.
    
    Args:
        db: Database session
        dry_run: If True, don't commit changes
    
    Returns:
        Number of documents fixed
    """
    logger.info("\n" + "-"*40)
    logger.info("Fixing source_file issues...")
    logger.info("-"*40)
    
    fixed_count = 0
    
    # Get documents with NULL source_file
    docs = db.query(Document).filter(
        (Document.source_file == None) | (Document.source_file == "None")
    ).all()
    
    for doc in docs:
        new_source = None
        
        # Try to derive from filepath
        if doc.filepath:
            new_source = doc.filepath
        # Try to derive from filename
        elif doc.filename and not "_untitled_" in (doc.filename or ""):
            new_source = f"original/{doc.filename}"
        
        if new_source:
            logger.info(f"  {doc.id}: NULL → {new_source[:50]}...")
            
            if not dry_run:
                doc.source_file = new_source
                fixed_count += 1
    
    if not dry_run:
        db.commit()
    
    logger.info(f"  Fixed {fixed_count} documents")
    return fixed_count


def fix_document_name_from_content(db: Session, dry_run: bool = True) -> int:
    """
    Fix document_name by extracting from first chunk content.
    
    Args:
        db: Database session
        dry_run: If True, don't commit changes
    
    Returns:
        Number of documents fixed
    """
    logger.info("\n" + "-"*40)
    logger.info("Fixing document_name from content...")
    logger.info("-"*40)
    
    fixed_count = 0
    
    # Get documents with problematic names
    docs = db.query(Document).filter(
        Document.document_name.like('%Untitled%')
    ).all()
    
    for doc in docs:
        # Get first chunk
        first_chunk = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == doc.id,
            DocumentChunk.chunk_index == 0
        ).first()
        
        if first_chunk:
            extracted_name = extract_document_name_from_content(first_chunk.content)
            
            if extracted_name and len(extracted_name) > 10:
                old_name = doc.document_name
                new_name = extracted_name
                
                logger.info(f"  {doc.id}:")
                logger.info(f"    OLD: {old_name[:60]}...")
                logger.info(f"    NEW: {new_name[:60]}...")
                
                if not dry_run:
                    doc.document_name = new_name
                    fixed_count += 1
    
    if not dry_run:
        db.commit()
    
    logger.info(f"  Fixed {fixed_count} documents")
    return fixed_count


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Analyze and fix document metadata quality issues"
    )
    parser.add_argument(
        "--analyze", 
        action="store_true",
        help="Only analyze, don't fix anything"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Fix issues (requires confirmation)"
    )
    parser.add_argument(
        "--issues",
        type=str,
        default="all",
        help="Comma-separated list of issues to fix: document_type,category,source_file,document_name (or 'all')"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be fixed without committing"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output analysis results to JSON file"
    )
    
    args = parser.parse_args()
    
    if not args.analyze and not args.fix:
        parser.print_help()
        print("\nError: Specify either --analyze or --fix")
        sys.exit(1)
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Always run analysis first
        results = analyze_documents(db)
        
        # Save results to file if requested
        if args.output:
            output_path = Path(args.output)
            with open(output_path, "w", encoding="utf-8") as f:
                # Convert UUIDs to strings for JSON
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"\nAnalysis saved to: {output_path}")
        
        # Fix issues if requested
        if args.fix:
            if not args.dry_run:
                logger.info("\n" + "="*60)
                logger.info("⚠️  THIS WILL MODIFY THE DATABASE")
                logger.info("="*60)
                confirm = input("Type 'yes' to confirm: ")
                if confirm.lower() != 'yes':
                    logger.info("Aborted.")
                    return
            
            # Determine which issues to fix
            issues_to_fix = args.issues.split(",") if args.issues != "all" else [
                "document_type", "category", "source_file", "document_name"
            ]
            
            logger.info(f"\nFixing issues: {', '.join(issues_to_fix)}")
            logger.info(f"Dry run: {args.dry_run}")
            
            total_fixed = 0
            
            if "document_type" in issues_to_fix:
                total_fixed += fix_document_type_issues(db, dry_run=args.dry_run)
            
            if "category" in issues_to_fix:
                total_fixed += fix_category_issues(db, dry_run=args.dry_run)
            
            if "source_file" in issues_to_fix:
                total_fixed += fix_source_file_issues(db, dry_run=args.dry_run)
            
            if "document_name" in issues_to_fix:
                total_fixed += fix_document_name_from_content(db, dry_run=args.dry_run)
            
            logger.info("\n" + "="*60)
            if args.dry_run:
                logger.info(f"DRY RUN: Would fix {total_fixed} issues")
            else:
                logger.info(f"✅ Fixed {total_fixed} issues")
            logger.info("="*60)
    
    finally:
        db.close()


if __name__ == "__main__":
    main()
