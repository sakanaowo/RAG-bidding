import os
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from app.core.config import settings

embeddings = OpenAIEmbeddings(model=settings.embed_model)

vector_store = PGVector(
    embeddings=embeddings,
    collection_name=settings.collection,
    connection_string=settings.database_url,
    use_jsonb=True,
    create_extension=True,
)


def bootstrap():
    vector_store.create_vector_extension()
    vector_store.create_tables_if_not_exists()
    vector_store.create_collection()
