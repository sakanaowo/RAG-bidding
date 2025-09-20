from app.core.vectorstore import bootstrap, vector_store

if __name__ == "__main__":
    vector_store.delete_collection()
    print("Collection deleted.")
    bootstrap()
    print("Collection rebuilt.")
