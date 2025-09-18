from langchain_postgres import PGEngine, PGVectorStore
from langchain_openai import OpenAIEmbeddings
from .config import PG_CONN, EMBED_MODEL, EMBED_DIM


def get_vector_store(table_name: "bidding_chunks"):
    engine = PGEngine.from_connection_string(PG_CONN)
    engine.init_vector(table_name, EMBED_DIM)
    emb = OpenAIEmbeddings(model_name=EMBED_MODEL)
    store = PGVectorStore.create_sync(
        embedding=emb, table_name=table_name, engine=engine
    )
    return store
