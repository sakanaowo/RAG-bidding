"""
Base Pipeline - Abstract class cho end-to-end document processing
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any


class BaseDocumentPipeline(ABC):
    """
    Abstract base class cho document processing pipelines

    Standard flow: Extract → Clean → Parse → Chunk → Export
    """

    @abstractmethod
    def process_single_file(
        self, file_path: str | Path, output_dir: str | Path
    ) -> Dict[str, Any]:
        """
        Process single document file

        Args:
            file_path: Path to input file
            output_dir: Directory for outputs

        Returns:
            Dictionary với results:
            {
                'file_path': str,
                'chunks': List[Chunk],
                'statistics': Dict,
                'metadata': Dict
            }

        Raises:
            FileNotFoundError: Input file not found
            ValueError: Processing error
        """
        pass

    @abstractmethod
    def process_batch(
        self,
        input_dir: str | Path,
        output_dir: str | Path,
        pattern: str = "**/*",
    ) -> Dict[str, Any]:
        """
        Process batch of documents

        Args:
            input_dir: Directory containing input files
            output_dir: Directory for outputs
            pattern: Glob pattern for file selection

        Returns:
            Dictionary với batch results:
            {
                'successful': int,
                'failed': int,
                'results': List[Dict]
            }
        """
        pass

    @abstractmethod
    def map_to_db_schema(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map processed data to database schema

        Args:
            processed_data: Output from process_single_file

        Returns:
            Dictionary mapped to DB schema fields
        """
        pass

    @abstractmethod
    def validate_output(self, output: Dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate pipeline output

        Args:
            output: Pipeline output to validate

        Returns:
            (is_valid, list_of_errors)
        """
        pass
