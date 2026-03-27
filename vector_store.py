from langchain_core.documents import Document

from project.config_hander import chroma_conf
from model.factory import embed_model
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os
from project.path_tool import get_abs_path
from project.logger_handler import logger
from  project.file_hander import pdf_loader,txt_loader,listdir_with_allowed_type,get_file_md5_hex

class VectorStoreService:
    def __init__(self):
        self.vector_store = Chroma(
            collection_name=chroma_conf["collection_name"], #表名
            embedding_function=embed_model,
            persist_directory=chroma_conf["persist_directory"], #存储路径
        )

        self.spiliter =RecursiveCharacterTextSplitter(
            chunk_size=chroma_conf["chunk_size"],
            chunk_overlap=chroma_conf["chunk_overlap"],
            separators=chroma_conf["separators"],
        )
    def get_retrive(self):
        return self.vector_store.as_retriever(search_kwargs={"k":chroma_conf["k"]})
    def load_document(self):
        """
        从数据文件夹内读取文件，转为向量存入向量库
        计算文件的md5值
        ：return：none
        """
        def check_md5_hex(md5_for_check:str):
            if not(os.path.exists(chroma_conf["md5_hex_store"])):

                open(get_abs_path(chroma_conf["md5_hex_store"]), "w",encoding="utf-8").close()
                return False    #md5未处理

            with open(get_abs_path(chroma_conf["md5_hex_store"]),"r",encoding="utf-8") as f:
                for line in f.readlines():
                    line = line.strip()
                    if line==md5_for_check:
                        return True
                return False

        def save_md5_hex(md5_for_check:str):
            with open(chroma_conf["md5_hex_store"],"a",encoding="utf-8") as f:
                f.write(md5_for_check+"\n")

        def get_file_documents(read_path:str):
            if read_path.endswith(".txt"):
                return txt_loader(read_path)

            if read_path.endswith(".pdf"):
                return pdf_loader(read_path)

            return []

        allowed_file_path=listdir_with_allowed_type(
            get_abs_path(chroma_conf["data_path"]),
            tuple(chroma_conf["allow_knowledge_file_type"]),
        )

        for path in allowed_file_path:
            #获取文件MD5
            md5_hex=get_file_md5_hex(path)

            if check_md5_hex(path):
                logger.info(f"[加载知识库]{path}内容已经存在知识库内，跳过")
                continue
            try:
                documents:list[Document] = get_file_documents(path)

                if not documents:
                    logger.warning(f"[加载知识库]{path}内容没有有效文本内容，跳过")
                    continue

                split_document:list[Document]=self.spiliter.split_documents(documents)

                if not split_document:
                    logger.warning(f"[加载知识库]{path}分片后没有有效内容，跳过")
                    continue

                #将内容存入向量库
                self.vector_store.add_documents(split_document)

                #记录这个已经处理好的文件md5，避免下次重复加载
                save_md5_hex(md5_hex)

                logger.info(f"[加载知识库 ]{path}内容加载成功")
            except Exception as e:
                #exc_info 为True会记录详细的报错堆栈，如果为false仅记录报错信息本身
                logger.error(f"[加载知识库]{path}加载失败,{str(e)}",exc_info=True)
                continue

if __name__=="__main__":
    vs = VectorStoreService()
    vs.load_document()

    retriever=vs.get_retrive()

    res=retriever.invoke("迷路")
    for r in res:
        print(r.page_content)
        print("="*20)