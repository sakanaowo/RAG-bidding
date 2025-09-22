import logging, sys, json, time
from datetime import datetime
from typing import Dict, Any, Optional
from app.core.config import settings


class JsonFormatter(logging.Formatter):
    def format(self, r: logging.LogRecord) -> str:
        base = {
            "level": r.levelname,
            "time": self.formatTime(r, self.datefmt),
            "message": r.getMessage(),
            "logger": r.name,
        }
        if r.exc_info:
            base["exc_info"] = self.formatException(r.exc_info)

        # Add extra fields if they exist
        for key, value in r.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
                "exc_info",
                "exc_text",
                "stack_info",
            ]:
                base[key] = value

        return json.dumps(base)


class ProcessingMetrics:
    """Track processing metrics and statistics."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset all metrics."""
        self.start_time = time.time()
        self.documents_processed = 0
        self.documents_failed = 0
        self.chunks_created = 0
        self.duplicates_found = 0
        self.validation_failures = 0
        self.processing_times = {}
        self.errors_by_type = {}

    def record_document_processed(self):
        """Record successful document processing."""
        self.documents_processed += 1

    def record_document_failed(self, error_type: str = "unknown"):
        """Record failed document processing."""
        self.documents_failed += 1
        self.errors_by_type[error_type] = self.errors_by_type.get(error_type, 0) + 1

    def record_chunks_created(self, count: int):
        """Record number of chunks created."""
        self.chunks_created += count

    def record_duplicates_found(self, count: int):
        """Record number of duplicates found."""
        self.duplicates_found += count

    def record_validation_failure(self):
        """Record validation failure."""
        self.validation_failures += 1

    def record_processing_time(self, operation: str, duration: float):
        """Record processing time for an operation."""
        if operation not in self.processing_times:
            self.processing_times[operation] = []
        self.processing_times[operation].append(duration)

    def get_summary(self) -> Dict[str, Any]:
        """Get processing summary."""
        total_time = time.time() - self.start_time

        summary = {
            "total_time_seconds": round(total_time, 2),
            "documents_processed": self.documents_processed,
            "documents_failed": self.documents_failed,
            "chunks_created": self.chunks_created,
            "duplicates_found": self.duplicates_found,
            "validation_failures": self.validation_failures,
            "success_rate": round(
                self.documents_processed
                / max(1, self.documents_processed + self.documents_failed)
                * 100,
                2,
            ),
            "processing_rate_docs_per_second": round(
                self.documents_processed / max(0.1, total_time), 2
            ),
            "errors_by_type": self.errors_by_type,
            "average_processing_times": {},
        }

        # Calculate average processing times
        for operation, times in self.processing_times.items():
            if times:
                summary["average_processing_times"][operation] = round(
                    sum(times) / len(times), 3
                )

        return summary


# Global metrics instance
processing_metrics = ProcessingMetrics()


class ProcessingLogger:
    """Enhanced logger for processing operations."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.metrics = processing_metrics

    def log_processing_start(self, operation: str, details: Optional[Dict] = None):
        """Log start of processing operation."""
        extra = {"operation": operation, "event": "start"}
        if details:
            extra.update(details)
        self.logger.info(f"Starting {operation}", extra=extra)

    def log_processing_end(
        self, operation: str, duration: float, details: Optional[Dict] = None
    ):
        """Log end of processing operation."""
        self.metrics.record_processing_time(operation, duration)
        extra = {
            "operation": operation,
            "event": "end",
            "duration_seconds": round(duration, 3),
        }
        if details:
            extra.update(details)
        self.logger.info(f"Completed {operation} in {duration:.3f}s", extra=extra)

    def log_document_processed(self, file_path: str, chunks_created: int = 0):
        """Log successful document processing."""
        self.metrics.record_document_processed()
        if chunks_created > 0:
            self.metrics.record_chunks_created(chunks_created)

        self.logger.info(
            f"Processed document: {file_path}",
            extra={
                "event": "document_processed",
                "file_path": file_path,
                "chunks_created": chunks_created,
            },
        )

    def log_document_failed(
        self, file_path: str, error: str, error_type: str = "unknown"
    ):
        """Log failed document processing."""
        self.metrics.record_document_failed(error_type)

        self.logger.error(
            f"Failed to process document: {file_path}",
            extra={
                "event": "document_failed",
                "file_path": file_path,
                "error": error,
                "error_type": error_type,
            },
        )

    def log_validation_result(
        self, valid_count: int, invalid_count: int, details: Optional[Dict] = None
    ):
        """Log validation results."""
        self.metrics.record_validation_failure()  # This will be called for each invalid document

        extra = {
            "event": "validation_result",
            "valid_documents": valid_count,
            "invalid_documents": invalid_count,
            "validation_rate": round(
                valid_count / max(1, valid_count + invalid_count) * 100, 2
            ),
        }
        if details:
            extra.update(details)

        self.logger.info(
            f"Validation completed: {valid_count} valid, {invalid_count} invalid",
            extra=extra,
        )

    def log_deduplication_result(
        self, unique_count: int, duplicate_count: int, details: Optional[Dict] = None
    ):
        """Log deduplication results."""
        self.metrics.record_duplicates_found(duplicate_count)

        extra = {
            "event": "deduplication_result",
            "unique_documents": unique_count,
            "duplicate_documents": duplicate_count,
            "deduplication_rate": round(
                duplicate_count / max(1, unique_count + duplicate_count) * 100, 2
            ),
        }
        if details:
            extra.update(details)

        self.logger.info(
            f"Deduplication completed: {unique_count} unique, {duplicate_count} duplicates",
            extra=extra,
        )

    def log_processing_summary(self):
        """Log processing summary."""
        summary = self.metrics.get_summary()

        self.logger.info(
            "Processing summary", extra={"event": "processing_summary", **summary}
        )

        return summary


def setup_logging():
    """Setup logging configuration."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    if settings.log_json:
        handler.setFormatter(JsonFormatter())
    else:
        # Enhanced formatter with timestamp
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)

    root.addHandler(handler)


def get_processing_logger(name: str) -> ProcessingLogger:
    """Get a processing logger instance."""
    return ProcessingLogger(name)


def reset_processing_metrics():
    """Reset global processing metrics."""
    global processing_metrics
    processing_metrics.reset()
