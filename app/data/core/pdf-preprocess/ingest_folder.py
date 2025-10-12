import argparse
import sys
from typing import Dict, Any
from config.logging_config import (
    setup_logging,
    get_processing_logger,
    reset_processing_metrics,
)
from src.embedding.store.pgvector_store import vector_store, bootstrap
from app.data.ingest_utils import load_folder, split_documents_with_validation
from app.data.exceptions import (
    handle_processing_error,
    DataProcessingError,
    VectorStoreError,
)

# Setup logging
setup_logging()
logger = get_processing_logger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Ingest documents from folder into vector store"
    )
    parser.add_argument("root", help="Root folder to ingest")
    parser.add_argument("--no-clean", action="store_true", help="Skip text cleaning")
    parser.add_argument(
        "--no-validate", action="store_true", help="Skip document validation"
    )
    parser.add_argument(
        "--no-deduplicate", action="store_true", help="Skip deduplication"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        import logging

        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Reset metrics for this ingestion session
        reset_processing_metrics()

        logger.log_processing_start(
            "document_ingestion",
            {
                "root_folder": args.root,
                "settings": {
                    "clean_text": not args.no_clean,
                    "validate_docs": not args.no_validate,
                    "deduplicate": not args.no_deduplicate,
                },
            },
        )

        # Load documents
        logger.logger.info(f"Loading documents from: {args.root}")
        raw_docs, load_stats = load_folder(
            args.root,
            clean_text=not args.no_clean,
            validate_docs=not args.no_validate,
            deduplicate=not args.no_deduplicate,
        )

        if not raw_docs:
            logger.logger.warning("No valid documents found to process")
            return 1

        logger.logger.info(f"Successfully loaded {len(raw_docs)} documents")

        # Split documents
        logger.logger.info("Splitting documents into chunks...")
        chunks, split_stats = split_documents_with_validation(raw_docs)

        if not chunks:
            logger.logger.error("No valid chunks created from documents")
            return 1

        logger.logger.info(
            f"Created {len(chunks)} chunks from {len(raw_docs)} documents"
        )

        # Initialize vector store
        logger.logger.info("Initializing vector store...")
        try:
            bootstrap()
        except Exception as e:
            raise VectorStoreError("initialization", str(e))

        # Add to vector store
        logger.logger.info("Adding chunks to vector store...")
        try:
            vector_store.add_documents(chunks)
        except Exception as e:
            raise VectorStoreError("document_insertion", str(e))

        # Final summary
        final_summary = {
            "ingestion_completed": True,
            "total_documents_processed": len(raw_docs),
            "total_chunks_created": len(chunks),
            "load_statistics": load_stats,
            "split_statistics": split_stats,
        }

        logger.log_processing_end("document_ingestion", 0, details=final_summary)

        # Print summary for user
        print(f"\n✅ Ingestion completed successfully!")
        print(f"📁 Documents processed: {len(raw_docs)}")
        print(f"📄 Chunks created: {len(chunks)}")
        print(
            f"⚡ Average chunk size: {split_stats.get('average_chunk_size', 0):.0f} characters"
        )

        if load_stats.get("validation"):
            val_stats = load_stats["validation"]
            print(
                f"✅ Validation: {val_stats['valid_docs']}/{val_stats['total_docs']} documents passed"
            )

        if load_stats.get("deduplication"):
            dedup_stats = load_stats["deduplication"]
            print(
                f"🔍 Deduplication: {dedup_stats['duplicate_docs']} duplicates removed"
            )

        if load_stats.get("processing_errors"):
            print(f"⚠️  Processing errors: {len(load_stats['processing_errors'])}")

        # Log final metrics summary
        logger.log_processing_summary()

        return 0

    except DataProcessingError as e:
        logger.logger.error(f"Data processing error: {e.message}")
        if e.details:
            for key, value in e.details.items():
                logger.logger.error(f"  {key}: {value}")
        return 1

    except Exception as e:
        logger.logger.error(
            f"Unexpected error during ingestion: {str(e)}", exc_info=True
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
