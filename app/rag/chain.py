import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from app.core.db import get_vector_store
from app.core.config import CHAT_MODEL

SYSTEM = (
    "Bạn là trợ lý pháp lý về ĐẤU THẦU. Chỉ trả lời dựa trên context được cung cấp. "
    "Luôn kèm mục 'Nguồn trích dẫn' liệt kê văn bản/điều/khoản/link nếu có. "
    "Nếu thiếu dữ liệu, nói rõ chưa đủ thông tin. Đây không phải tư vấn pháp lý."
)

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM),
        (
            "human",
            "Câu hỏi: {input}\n\n"
            "Context:\n{context}\n\n"
            "Trả lời ngắn gọn, súc tích bằng tiếng Việt, kèm mục 'Nguồn trích dẫn' nếu có.",
        ),
    ]
)


def build_chain(k: int = 5):
    store = get_vector_store()
    retriever = store.as_retriever(search_type="similarity", search_kwargs={"k": k})
    llm = ChatOpenAI(model_name=CHAT_MODEL, temperature=0)
    doc_chain = create_stuff_documents_chain(llm=llm, prompt=PROMPT)

    rag_core = ({"context": retriever, "input": RunnablePassthrough()}) | doc_chain
    chain = RunnableParallel(answer=rag_core, sources=retriever)
    return chain
