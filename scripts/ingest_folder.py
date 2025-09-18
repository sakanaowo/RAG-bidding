import uuid, os
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

from app.core.db import get_vector_store


def chunk_text(text: str):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
    )
    return splitter.split_text(text)


def ingest_folder(dir_path: str):
    store = get_vector_store()
    for pdf in Path(dir_path).glob("*.pdf"):
        pages = PyPDFLoader(str(pdf)).load_and_split()
        full = "\n".join([p.page_content for p in pages])
        chunks = chunk_text(full)

        doc = [
            Document(
                page_content=c,
                metadata={
                    "title": pdf.stem,
                    "code": None,  # code of law
                    "doc_type": "law",  # law, regulation, guideline, ...
                    "effective_from": None,  # date
                    "effective_to": None,  # date
                    "source_url": None,
                    "heading_path": "",  # e.g. "Chapter 1 > Article 2 > ..."
                },
            )
            for c in chunks
        ]
        store.add_documents(doc)
        print(f"Ingested {pdf.name}, {len(chunks)} chunks")


if __name__ == "__main__":
    import sys

    ingest_folder(sys.argv[1] if len(sys.argv) > 1 else "./samples_pdfs")
