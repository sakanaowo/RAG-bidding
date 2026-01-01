"""
Example Usage: ProcessingStatus Field

Demonstrates how to use the new processing_status field to track
document processing through the pipeline.

See: documents/technical/CHUNKING_REFACTORING_STATUS_FIELD.md
"""

from datetime import datetime
from src.preprocessing.schema import (
    UnifiedLegalChunk,
    ProcessingMetadata,
    ProcessingStage,
    ProcessingStatus,
)


# ============================================================
# EXAMPLE 1: Setting status during pipeline stages
# ============================================================


def example_pipeline_progression():
    """Example of status transitions through pipeline"""

    # Create ProcessingMetadata
    metadata = ProcessingMetadata(
        processing_id="proc_20251109_001",
        pipeline_version="2.0.0",
    )

    print("=== Pipeline Progression Example ===\n")

    # Stage 1: Start ingestion
    metadata.current_stage = ProcessingStage.INGESTION
    metadata.processing_status = ProcessingStatus.IN_PROGRESS
    print(f"Stage: {metadata.current_stage}, Status: {metadata.processing_status}")

    # Stage 2: Ingestion completed
    metadata.completed_stages.append(ProcessingStage.INGESTION)
    metadata.processing_status = ProcessingStatus.COMPLETED
    print(f"✓ Ingestion completed")

    # Stage 3: Start chunking
    metadata.current_stage = ProcessingStage.CHUNKING
    metadata.processing_status = ProcessingStatus.IN_PROGRESS
    print(f"Stage: {metadata.current_stage}, Status: {metadata.processing_status}")

    # Stage 4: Chunking completed
    metadata.completed_stages.append(ProcessingStage.CHUNKING)
    metadata.processing_status = ProcessingStatus.COMPLETED
    print(f"✓ Chunking completed")

    # Stage 5: Start enrichment
    metadata.current_stage = ProcessingStage.ENRICHMENT
    metadata.processing_status = ProcessingStatus.IN_PROGRESS
    print(f"Stage: {metadata.current_stage}, Status: {metadata.processing_status}")

    # Stage 6: Final success
    metadata.completed_stages.append(ProcessingStage.ENRICHMENT)
    metadata.processing_status = ProcessingStatus.COMPLETED
    print(f"✓ All processing completed!")
    print(f"Final status: {metadata.processing_status}")


# ============================================================
# EXAMPLE 2: Handling errors with retry logic
# ============================================================


def example_error_handling():
    """Example of handling failures and retries"""

    metadata = ProcessingMetadata(
        processing_id="proc_20251109_002",
        pipeline_version="2.0.0",
    )

    print("\n=== Error Handling Example ===\n")

    # Attempt 1: Chunking fails
    metadata.current_stage = ProcessingStage.CHUNKING
    metadata.processing_status = ProcessingStatus.IN_PROGRESS

    try:
        # Simulate chunking error
        raise ValueError("Invalid document structure detected")
    except Exception as e:
        metadata.processing_status = ProcessingStatus.FAILED
        metadata.error_message = str(e)
        metadata.errors_encountered.append(str(e))
        print(f"❌ Chunking failed: {metadata.error_message}")

    # Mark for retry
    metadata.processing_status = ProcessingStatus.RETRY
    metadata.retry_count += 1
    metadata.last_retry_at = datetime.now()
    print(f"⚠️  Marked for retry (attempt #{metadata.retry_count})")

    # Attempt 2: Success after retry
    metadata.processing_status = ProcessingStatus.IN_PROGRESS
    print(f"🔄 Retrying chunking...")

    # Simulate success
    metadata.processing_status = ProcessingStatus.COMPLETED
    metadata.completed_stages.append(ProcessingStage.CHUNKING)
    metadata.error_message = None  # Clear error
    print(f"✓ Retry successful!")
    print(f"Final status: {metadata.processing_status}")


# ============================================================
# EXAMPLE 3: Querying documents by status
# ============================================================


def example_status_queries():
    """Example queries to find documents by status"""

    print("\n=== Status Query Examples ===\n")

    # Example PostgreSQL queries
    queries = {
        "Find all failed documents": """
            SELECT chunk_id, error_message
            FROM chunks
            WHERE processing_metadata->>'processing_status' = 'failed';
        """,
        "Find documents stuck in processing": """
            SELECT chunk_id, current_stage, processed_at
            FROM chunks
            WHERE processing_metadata->>'processing_status' = 'in_progress'
              AND processed_at < NOW() - INTERVAL '1 hour';
        """,
        "Find documents ready for retry": """
            SELECT chunk_id, retry_count, last_retry_at
            FROM chunks
            WHERE processing_metadata->>'processing_status' = 'retry'
              AND (last_retry_at IS NULL OR last_retry_at < NOW() - INTERVAL '5 minutes');
        """,
        "Get processing success rate": """
            SELECT 
                processing_metadata->>'processing_status' as status,
                COUNT(*) as count,
                ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
            FROM chunks
            GROUP BY status
            ORDER BY count DESC;
        """,
    }

    for description, query in queries.items():
        print(f"📊 {description}:")
        print(query)
        print()


# ============================================================
# EXAMPLE 4: Partial success handling
# ============================================================


def example_partial_success():
    """Example of handling partial success (some chunks fail)"""

    metadata = ProcessingMetadata(
        processing_id="proc_20251109_003",
        pipeline_version="2.0.0",
    )

    print("\n=== Partial Success Example ===\n")

    # Process 10 chunks, 8 succeed, 2 fail
    total_chunks = 10
    successful_chunks = 8
    failed_chunks = 2

    metadata.current_stage = ProcessingStage.CHUNKING
    metadata.processing_status = ProcessingStatus.IN_PROGRESS

    print(f"Processing {total_chunks} chunks...")

    # Some chunks failed
    if failed_chunks > 0:
        metadata.processing_status = ProcessingStatus.PARTIAL
        metadata.warnings.append(
            f"{failed_chunks}/{total_chunks} chunks failed to process"
        )
        print(
            f"⚠️  Partial success: {successful_chunks}/{total_chunks} chunks processed"
        )
    else:
        metadata.processing_status = ProcessingStatus.COMPLETED
        print(f"✓ All {total_chunks} chunks processed successfully")

    print(f"Final status: {metadata.processing_status}")


# ============================================================
# EXAMPLE 5: Skip duplicate documents
# ============================================================


def example_skip_duplicate():
    """Example of skipping duplicate documents"""

    metadata = ProcessingMetadata(
        processing_id="proc_20251109_004",
        pipeline_version="2.0.0",
    )

    print("\n=== Skip Duplicate Example ===\n")

    # Check if document already exists
    doc_id = "43/2024/NĐ-CP"
    is_duplicate = True  # Simulate duplicate detection

    if is_duplicate:
        metadata.processing_status = ProcessingStatus.SKIPPED
        metadata.warnings.append(f"Document {doc_id} already exists in database")
        print(f"⏭️  Document {doc_id} skipped (duplicate)")
    else:
        metadata.processing_status = ProcessingStatus.IN_PROGRESS
        print(f"Processing new document {doc_id}...")

    print(f"Final status: {metadata.processing_status}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    example_pipeline_progression()
    example_error_handling()
    example_status_queries()
    example_partial_success()
    example_skip_duplicate()

    print("\n" + "=" * 60)
    print("✅ All examples completed!")
    print("=" * 60)
    print(
        "\nSee documentation: documents/technical/CHUNKING_REFACTORING_STATUS_FIELD.md"
    )
