from ..query_processing import QueryEnhancer, QueryEnhancerConfig, EnhancementStrategy


class AdaptiveRetriever:
    def __init__(self, vector_store, use_query_enhancement=True):
        self.vector_store = vector_store

        # Add query enhancer
        if use_query_enhancement:
            config = QueryEnhancerConfig(
                strategies=[EnhancementStrategy.MULTI_QUERY], max_queries=3
            )
            self.query_enhancer = QueryEnhancer(config)
        else:
            self.query_enhancer = None

    def retrieve(self, query: str, k: int = 5):
        # Enhance query if enabled
        if self.query_enhancer:
            queries = self.query_enhancer.enhance(query)
        else:
            queries = [query]

        # Retrieve for each query
        all_docs = []
        for q in queries:
            docs = self.vector_store.similarity_search(q, k=k)
            all_docs.extend(docs)

        # Deduplicate and limit
        unique_docs = self._deduplicate_docs(all_docs)
        return unique_docs[:k]

    def _deduplicate_docs(self, all_docs):
        """Remove duplicate documents based on page_content."""
        seen = set()
        unique_docs = []

        for doc in all_docs:
            # Sử dụng hash của content để check duplicate
            content_hash = hash(doc.page_content)
            if content_hash not in seen:
                seen.add(content_hash)
                unique_docs.append(doc)

        return unique_docs
