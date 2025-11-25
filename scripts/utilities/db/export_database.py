#!/usr/bin/env python3
"""
Database Export Utility
Export embeddings and metadata from PostgreSQL database to various formats
"""

import os
import json
import csv
import pickle
import numpy as np
from datetime import datetime
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
import argparse
from typing import List, Dict, Any, Optional
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DatabaseExporter:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.conn = None

    def connect(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(self.connection_string)
            logger.info("Connected to database successfully")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def get_collections_info(self) -> List[Dict]:
        """Get information about all collections"""
        query = """
        SELECT 
            c.uuid,
            c.name,
            c.cmetadata,
            COUNT(e.id) as embedding_count,
            vector_dims(e.embedding) as dimensions
        FROM langchain_pg_collection c 
        LEFT JOIN langchain_pg_embedding e ON c.uuid = e.collection_id 
        GROUP BY c.uuid, c.name, c.cmetadata, vector_dims(e.embedding)
        """

        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query)
            return cursor.fetchall()

    def export_embeddings_bulk(
        self,
        collection_name: str,
        output_dir: Path,
        formats: List[str] = ["json", "csv", "numpy"],
    ):
        """Export embeddings in multiple formats"""
        logger.info(f"Exporting collection: {collection_name}")

        # Get collection UUID
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT uuid FROM langchain_pg_collection WHERE name = %s",
                (collection_name,),
            )
            collection_uuid = cursor.fetchone()[0]

        # Export embeddings with metadata
        query = """
        SELECT 
            e.id,
            e.document,
            e.cmetadata,
            e.embedding::text as embedding_vector,
            e.custom_id
        FROM langchain_pg_embedding e 
        WHERE e.collection_id = %s
        ORDER BY e.id
        """

        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (collection_uuid,))

            embeddings_data = []
            vectors = []

            logger.info("Fetching embeddings from database...")
            for row in cursor:
                # Parse vector string to numpy array
                vector_str = row["embedding_vector"].strip("[]")
                vector = np.fromstring(vector_str, sep=",", dtype=np.float32)
                vectors.append(vector)

                # Prepare row data
                row_data = {
                    "id": row["id"],
                    "document": row["document"],
                    "metadata": row["cmetadata"],
                    "custom_id": row["custom_id"],
                }
                embeddings_data.append(row_data)

                if len(embeddings_data) % 100 == 0:
                    logger.info(f"Processed {len(embeddings_data)} embeddings...")

        logger.info(f"Total embeddings exported: {len(embeddings_data)}")

        # Convert to numpy array
        vectors_array = np.array(vectors)

        # Export in different formats
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if "json" in formats:
            self._export_json(
                embeddings_data, vectors_array, output_dir, collection_name, timestamp
            )

        if "csv" in formats:
            self._export_csv(embeddings_data, output_dir, collection_name, timestamp)

        if "numpy" in formats:
            self._export_numpy(
                embeddings_data, vectors_array, output_dir, collection_name, timestamp
            )

        if "pickle" in formats:
            self._export_pickle(
                embeddings_data, vectors_array, output_dir, collection_name, timestamp
            )

        return len(embeddings_data)

    def _export_json(
        self,
        embeddings_data: List[Dict],
        vectors: np.ndarray,
        output_dir: Path,
        collection_name: str,
        timestamp: str,
    ):
        """Export to JSON format"""
        json_file = output_dir / f"{collection_name}_embeddings_{timestamp}.json"

        export_data = {
            "metadata": {
                "collection_name": collection_name,
                "export_timestamp": timestamp,
                "total_embeddings": len(embeddings_data),
                "embedding_dimensions": vectors.shape[1] if len(vectors) > 0 else 0,
            },
            "embeddings": [],
        }

        for i, data in enumerate(embeddings_data):
            item = data.copy()
            item["embedding"] = vectors[i].tolist()
            export_data["embeddings"].append(item)

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        logger.info(f"JSON export saved to: {json_file}")

    def _export_csv(
        self,
        embeddings_data: List[Dict],
        output_dir: Path,
        collection_name: str,
        timestamp: str,
    ):
        """Export metadata to CSV format (without embeddings due to size)"""
        csv_file = output_dir / f"{collection_name}_metadata_{timestamp}.csv"

        if not embeddings_data:
            return

        # Get all metadata keys
        all_keys = set()
        for data in embeddings_data:
            if data["metadata"]:
                all_keys.update(data["metadata"].keys())
        all_keys = sorted(list(all_keys))

        fieldnames = ["id", "custom_id", "document_preview"] + [
            f"metadata_{key}" for key in all_keys
        ]

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for data in embeddings_data:
                row = {
                    "id": data["id"],
                    "custom_id": data["custom_id"],
                    "document_preview": (
                        data["document"][:200] + "..."
                        if len(data["document"]) > 200
                        else data["document"]
                    ),
                }

                # Add metadata fields
                if data["metadata"]:
                    for key in all_keys:
                        row[f"metadata_{key}"] = data["metadata"].get(key, "")

                writer.writerow(row)

        logger.info(f"CSV metadata export saved to: {csv_file}")

    def _export_numpy(
        self,
        embeddings_data: List[Dict],
        vectors: np.ndarray,
        output_dir: Path,
        collection_name: str,
        timestamp: str,
    ):
        """Export vectors to NumPy format"""
        numpy_file = output_dir / f"{collection_name}_vectors_{timestamp}.npz"

        # Prepare metadata arrays
        ids = np.array([data["id"] for data in embeddings_data])
        custom_ids = np.array([data["custom_id"] or "" for data in embeddings_data])

        np.savez_compressed(
            numpy_file,
            vectors=vectors,
            ids=ids,
            custom_ids=custom_ids,
            metadata={
                "collection_name": collection_name,
                "export_timestamp": timestamp,
                "total_embeddings": len(embeddings_data),
                "embedding_dimensions": vectors.shape[1] if len(vectors) > 0 else 0,
            },
        )

        logger.info(f"NumPy export saved to: {numpy_file}")

    def _export_pickle(
        self,
        embeddings_data: List[Dict],
        vectors: np.ndarray,
        output_dir: Path,
        collection_name: str,
        timestamp: str,
    ):
        """Export to pickle format (complete data)"""
        pickle_file = output_dir / f"{collection_name}_complete_{timestamp}.pkl"

        export_data = {
            "metadata": {
                "collection_name": collection_name,
                "export_timestamp": timestamp,
                "total_embeddings": len(embeddings_data),
                "embedding_dimensions": vectors.shape[1] if len(vectors) > 0 else 0,
            },
            "embeddings_data": embeddings_data,
            "vectors": vectors,
        }

        with open(pickle_file, "wb") as f:
            pickle.dump(export_data, f)

        logger.info(f"Pickle export saved to: {pickle_file}")

    def export_database_schema(self, output_dir: Path):
        """Export database schema"""
        schema_file = (
            output_dir
            / f"database_schema_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        )

        # Get schema using pg_dump
        import subprocess

        # Extract connection details
        conn_parts = self.connection_string.split("/")
        db_name = conn_parts[-1]

        cmd = f"pg_dump -U sakana -h localhost -s -d {db_name} > {schema_file}"

        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Database schema exported to: {schema_file}")
            else:
                logger.error(f"Schema export failed: {result.stderr}")
        except Exception as e:
            logger.error(f"Failed to export schema: {e}")


def main():
    parser = argparse.ArgumentParser(description="Export RAG database")
    parser.add_argument(
        "--collection", "-c", default="docs", help="Collection name to export"
    )
    parser.add_argument("--output-dir", "-o", help="Output directory")
    parser.add_argument(
        "--formats",
        "-f",
        nargs="+",
        choices=["json", "csv", "numpy", "pickle"],
        default=["json", "csv", "numpy"],
        help="Export formats",
    )
    parser.add_argument(
        "--include-schema", action="store_true", help="Include database schema"
    )

    args = parser.parse_args()

    # Setup output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(f"backup/exports/{timestamp}")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Database connection string
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://sakana:sakana123@localhost:5432/rag_bidding_v2",
    )
    # Convert to psycopg2 format
    if db_url.startswith("postgresql+psycopg://"):
        db_url = db_url.replace("postgresql+psycopg://", "postgresql://")

    # Export data
    exporter = DatabaseExporter(db_url)

    try:
        exporter.connect()

        # Show collections info
        collections = exporter.get_collections_info()
        logger.info("Available collections:")
        for col in collections:
            logger.info(
                f"  - {col['name']}: {col['embedding_count']} embeddings, {col['dimensions']} dimensions"
            )

        # Export specified collection
        if args.collection in [col["name"] for col in collections]:
            count = exporter.export_embeddings_bulk(
                args.collection, output_dir, args.formats
            )
            logger.info(
                f"Successfully exported {count} embeddings from collection '{args.collection}'"
            )
        else:
            logger.error(f"Collection '{args.collection}' not found")
            return

        # Export schema if requested
        if args.include_schema:
            exporter.export_database_schema(output_dir)

        # Create summary file
        summary_file = output_dir / "export_summary.txt"
        with open(summary_file, "w") as f:
            f.write(f"RAG Database Export Summary\n")
            f.write(f"===========================\n\n")
            f.write(f"Export Date: {datetime.now()}\n")
            f.write(f"Collection: {args.collection}\n")
            f.write(f"Total Embeddings: {count}\n")
            f.write(f"Formats: {', '.join(args.formats)}\n")
            f.write(f"Output Directory: {output_dir.absolute()}\n\n")

            f.write("Exported Files:\n")
            for file_path in sorted(output_dir.glob("*")):
                if file_path.is_file():
                    size = file_path.stat().st_size / (1024 * 1024)  # MB
                    f.write(f"  - {file_path.name} ({size:.2f} MB)\n")

        logger.info(f"Export summary saved to: {summary_file}")
        logger.info(f"All files exported to: {output_dir.absolute()}")

    finally:
        exporter.disconnect()


if __name__ == "__main__":
    main()
