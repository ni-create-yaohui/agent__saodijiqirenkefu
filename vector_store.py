
from project.config_hander import chroma_conf
from model.factory import embed_model
from langchain_chroma import Chroma

class VectorStoreService:
    def __init__(self):
        self.vector_store = Chroma(
            collection_name=chroma_conf["collection_name"], #表名
            embedding_function=embed_model,
            persist_directory=chroma_conf["persist_directory"], #存储路径
        )
    def get_retrive(self):
        return self.vector_store.as_retriever(search_kwargs={"k":chroma_conf["k"]})