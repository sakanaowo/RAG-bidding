import argparse
from app.core.logging import setup_logging
from app.core.vectorstore import vector_store, bootstrap
from app.data.ingest_utils import load_folder, text_splitter

setup_logging()

parser = argparse.ArgumentParser()
parser.add_argument("root", help="Root folder to ingest")
args = parser.parse_args()

raw_docs = load_folder(args.root)
chunks = text_splitter.split_documents(raw_docs)

bootstrap()
vector_store.add_documents(chunks)
print(f"Ingested {len(chunks)} chunks from {len(raw_docs)} documents.")
