from pathlib import Path
from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import settings

ALLOWED_EXT = {e.strip().lower() for e in settings.allowed_ext}


def load_folder(root: str) -> List[Document]:
    docs: List[Document] = []
    for p in Path(root).rglob("*"):
        if not p.is_file():
            continue
        suf = p.suffix.lower()
        if suf not in ALLOWED_EXT:
            continue
        if suf in {".txt", ".md"}:
            text = p.read_text(encoding="utf-8", errors="ignore")
            docs.append(
                Document(page_content=text, metadata={"path": str(p.resolve())})
            )
        elif suf == ".pdf":
            from langchain_pdf import PDFLoader

            loader = PDFLoader(str(p.resolve()))
            docs.extend(loader.load())
    return docs


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap
)
