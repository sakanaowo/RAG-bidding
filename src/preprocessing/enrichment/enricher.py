"""
Chunk Enricher - Main orchestrator for enriching chunks with metadata.

Combines all extractors to add semantic metadata to chunks.
"""

from typing import Dict, List, Any
from dataclasses import asdict

from .extractor import LegalEntityExtractor
from .concept_extractor import LegalConceptExtractor
from .keyword_extractor import KeywordExtractor


class ChunkEnricher:
    """
    Enrich chunks with semantic metadata from all extractors.

    Adds:
    - Legal entities (NER): laws, decrees, dates, organizations
    - Legal concepts: bidding terms, contract terms, procedures
    - Keywords: TF-IDF based important terms
    - Document focus: primary topic category
    """

    def __init__(self):
        self.entity_extractor = LegalEntityExtractor()
        self.concept_extractor = LegalConceptExtractor()
        self.keyword_extractor = KeywordExtractor()

    def enrich_chunk(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a single chunk with all metadata.

        Args:
            chunk: Chunk dict with 'text' or 'content' key and optional 'metadata'

        Returns:
            Enhanced chunk with enriched metadata
        """
        # Support both 'text' and 'content' keys
        text = chunk.get("text", chunk.get("content", ""))

        if not text:
            return chunk

        # Extract all metadata
        entities = self.entity_extractor.extract_as_metadata(text)
        concepts = self.concept_extractor.extract_as_metadata(text)
        keywords = self.keyword_extractor.extract_as_metadata(text)

        # Identify document focus
        focus = self.concept_extractor.identify_document_focus(text)

        # Build enrichment metadata
        enrichment = {
            # Entities (NER)
            "entities": entities,
            "referenced_laws": entities["laws"],
            "referenced_decrees": entities["decrees"],
            "referenced_circulars": entities["circulars"],
            "referenced_dates": entities["dates"],
            "organizations": entities["organizations"],
            # Concepts
            "concepts": concepts["concepts"],
            "concept_categories": concepts["concept_categories"],
            "primary_concepts": concepts["primary_concepts"],
            "document_focus": focus,
            # Keywords
            "keywords": keywords["keywords"],
            "legal_terms": keywords["legal_terms"],
            # Enrichment metadata
            "enriched": True,
            "enrichment_version": "1.0.0",
        }

        # Merge with existing metadata
        if "metadata" not in chunk:
            chunk["metadata"] = {}

        chunk["metadata"].update(enrichment)

        return chunk

    def enrich_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich multiple chunks.

        Args:
            chunks: List of chunk dicts

        Returns:
            List of enriched chunks
        """
        enriched_chunks = []

        for i, chunk in enumerate(chunks):
            try:
                enriched = self.enrich_chunk(chunk)
                enriched_chunks.append(enriched)
            except Exception as e:
                print(f"⚠️  Warning: Failed to enrich chunk {i}: {e}")
                # Add unenriched chunk with error flag
                chunk["metadata"] = chunk.get("metadata", {})
                chunk["metadata"]["enrichment_error"] = str(e)
                chunk["metadata"]["enriched"] = False
                enriched_chunks.append(chunk)

        return enriched_chunks

    def get_enrichment_stats(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get statistics about enrichment results.

        Returns:
            Dict with enrichment statistics
        """
        stats = {
            "total_chunks": len(chunks),
            "enriched_chunks": 0,
            "failed_chunks": 0,
            "total_entities": 0,
            "total_concepts": 0,
            "total_keywords": 0,
            "document_focuses": {},
        }

        for chunk in chunks:
            metadata = chunk.get("metadata", {})

            if metadata.get("enriched"):
                stats["enriched_chunks"] += 1

                # Count entities
                entities = metadata.get("entities", {})
                for entity_list in entities.values():
                    stats["total_entities"] += len(entity_list)

                # Count concepts
                concepts = metadata.get("concepts", [])
                stats["total_concepts"] += len(concepts)

                # Count keywords
                keywords = metadata.get("keywords", [])
                stats["total_keywords"] += len(keywords)

                # Track document focus distribution
                focus = metadata.get("document_focus", "unknown")
                stats["document_focuses"][focus] = (
                    stats["document_focuses"].get(focus, 0) + 1
                )
            else:
                stats["failed_chunks"] += 1

        # Calculate averages
        if stats["enriched_chunks"] > 0:
            stats["avg_entities_per_chunk"] = (
                stats["total_entities"] / stats["enriched_chunks"]
            )
            stats["avg_concepts_per_chunk"] = (
                stats["total_concepts"] / stats["enriched_chunks"]
            )
            stats["avg_keywords_per_chunk"] = (
                stats["total_keywords"] / stats["enriched_chunks"]
            )

        return stats
