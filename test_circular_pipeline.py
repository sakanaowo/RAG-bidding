#!/usr/bin/env python3
"""
Test Circular Preprocessing Pipeline

Test the complete Circular preprocessing pipeline with sample documents.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path  
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.preprocessing.circular_preprocessing import CircularPreprocessingPipeline

def test_circular_pipeline():
    """Test circular preprocessing pipeline with sample documents"""
    
    # Configuration
    raw_data_dir = project_root / "data" / "raw" / "Thong tu"
    output_dir = project_root / "data" / "processed" / "circular_test"
    
    print("=" * 80)
    print("TESTING CIRCULAR PREPROCESSING PIPELINE")
    print("=" * 80)
    print(f"Project root: {project_root}")
    print(f"Raw data: {raw_data_dir}")
    print(f"Output: {output_dir}\n")
    
    # Check if data directory exists
    if not raw_data_dir.exists():
        print(f"❌ Raw data directory not found: {raw_data_dir}")
        print("Looking for alternative paths...")
        
        # Try alternative paths
        alt_paths = [
            project_root / "data" / "raw" / "Thong tu",
            project_root / "data" / "raw" / "thong-tu", 
            project_root / "data" / "raw" / "Circular",
        ]
        
        for alt_path in alt_paths:
            if alt_path.exists():
                raw_data_dir = alt_path
                print(f"✅ Found alternative path: {raw_data_dir}")
                break
        else:
            print("❌ No circular data directory found")
            return False
    
    # Find DOCX files
    docx_files = list(raw_data_dir.glob("*.docx"))
    
    if not docx_files:
        print(f"❌ No .docx files found in {raw_data_dir}")
        print("Directory contents:")
        if raw_data_dir.exists():
            for item in raw_data_dir.iterdir():
                print(f"  - {item.name}")
        return False
    
    print(f"✅ Found {len(docx_files)} DOCX files:")
    for docx_file in docx_files:
        print(f"  - {docx_file.name}")
    
    # Initialize pipeline
    print("\n📦 Initializing Circular Preprocessing Pipeline...")
    pipeline = CircularPreprocessingPipeline(
        chunk_size_range=(300, 2000),
        validate_integrity=True,  
        chunking_strategy="optimal_hybrid"
    )
    
    print("✅ Pipeline initialized")
    print(f"   Components: {pipeline.get_statistics()['components']}")
    
    # Process first document (or specific one)
    test_file = docx_files[0]
    
    # Look for specific test files
    preferred_files = [
        "0. Lời văn thông tư.docx",
        "00. Quyết định Thông tư.docx",
        "Thông tư.docx"
    ]
    
    for preferred_name in preferred_files:
        preferred_file = raw_data_dir / preferred_name
        if preferred_file.exists():
            test_file = preferred_file
            break
    
    print(f"\n🎯 Processing test file: {test_file.name}")
    print(f"   File size: {test_file.stat().st_size:,} bytes")
    
    try:
        # Process document
        results = pipeline.process_single_file(test_file, output_dir)
        
        print(f"\n✅ PROCESSING SUCCESSFUL!")
        print(f"   Chunks created: {len(results['chunks'])}")
        print(f"   DB records: {len(results['db_chunks'])}")
        
        # Display some statistics
        stats = results['statistics']
        print(f"\n📊 STATISTICS:")
        orig_chars = stats.get('original_chars', 'N/A')
        clean_chars = stats.get('cleaned_chars', 'N/A')
        avg_chunk = stats.get('avg_chunk_size', 'N/A')
        
        print(f"   Original chars: {orig_chars:,}" if isinstance(orig_chars, int) else f"   Original chars: {orig_chars}")
        print(f"   Cleaned chars: {clean_chars:,}" if isinstance(clean_chars, int) else f"   Cleaned chars: {clean_chars}")
        print(f"   Structure nodes: {stats.get('total_nodes', 'N/A')}")
        print(f"   Chunks: {stats.get('total_chunks', len(results['chunks']))}")
        print(f"   Avg chunk size: {avg_chunk:.0f}" if isinstance(avg_chunk, (int, float)) else f"   Avg chunk size: {avg_chunk}")
        
        # Show sample chunk
        if results['db_chunks']:
            sample_chunk = results['db_chunks'][0]
            sample_text = results['chunks'][0].text[:200] + "..."
            print(f"\n📝 SAMPLE CHUNK:")
            print(f"   Hierarchy: {sample_chunk.get('hierarchy', 'N/A')}")
            print(f"   Level: {sample_chunk.get('level', 'N/A')}")
            print(f"   Text preview: {sample_text}")
        
        # Data integrity results
        if 'integrity_report' in results:
            integrity = results['integrity_report']
            print(f"\n🔍 DATA INTEGRITY:")
            print(f"   Coverage: {integrity.coverage_percentage:.1f}%")
            print(f"   Checks: {integrity.passed_checks}/{integrity.total_checks} passed")
            print(f"   Status: {'✅ VALID' if integrity.is_valid else '⚠️ WARNINGS'}")
            
            if integrity.warnings:
                print(f"   Warnings: {len(integrity.warnings)}")
                for warning in integrity.warnings[:2]:
                    print(f"     - {warning}")
            
            if integrity.errors:
                print(f"   Errors: {len(integrity.errors)}")
                for error in integrity.errors[:2]:
                    print(f"     - {error}")
        
        print(f"\n💾 OUTPUT FILES:")
        for output_file in output_dir.glob(f"{test_file.stem}*"):
            print(f"   - {output_file.name}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ PROCESSING FAILED!")
        print(f"   Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_circular_pipeline()
    
    if success:
        print(f"\n" + "=" * 80)
        print("✅ CIRCULAR PIPELINE TEST COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        sys.exit(0)
    else:
        print(f"\n" + "=" * 80)
        print("❌ CIRCULAR PIPELINE TEST FAILED!")
        print("=" * 80)
        sys.exit(1)