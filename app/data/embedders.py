from typing import List, Protocol
import os, numpy as np


class Embedder(Protocol):
    def embed(self, texts: List[str]) -> List[List[float]]: ...


class OpenAIEmbedder:
    def __init__(self, model: str):
        from openai import OpenAI

        self.client = OpenAI()
        self.model = model

    def embed(self, texts: List[str]) -> List[List[float]]:
        response = self.client.embeddings.create(model=self.model, input=texts)
        return [data.embedding for data in response.data]


# 2) Ollama (local)
class OllamaEmbedder:
    def __init__(self, model: str = "nomic-embed-text"):
        import httpx

        self.model = model
        self.http = httpx.Client(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        )

    def embed(self, texts: List[str]) -> List[List[float]]:
        out = []
        for t in texts:
            r = self.http.post(
                "/api/embeddings", json={"model": self.model, "prompt": t}
            )
            r.raise_for_status()
            out.append(r.json()["embedding"])
        return out


# 3) Sentence-Transformers
class SbertEmbedder:
    def __init__(self, model: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model)

    def embed(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(texts, normalize_embeddings=True).tolist()
