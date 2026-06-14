"""
Hybrid RAG pipeline — keyword + vector search with reranking.
"""

from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document

class HybridRAGPipeline:
    def __init__(self, collection_name: str = "hybrid_rag"):
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )

    def ingest(self, documents: list[Document]):
        chunks = self.text_splitter.split_documents(documents)
        self.vectorstore.add_documents(chunks)
        return len(chunks)

    def retrieve(self, query: str, k: int = 4):
        docs = self.vectorstore.similarity_search_with_relevance_scores(query, k=k)
        return [(doc.page_content, score) for doc, score in docs]

    def hybrid_retrieve(self, query: str, k: int = 4):
        vector_results = self.vectorstore.similarity_search(query, k=k)

        keyword_filter = [d for d in vector_results
                         if any(w in d.page_content.lower()
                               for w in query.lower().split())]

        return keyword_filter or vector_results

rag = HybridRAGPipeline()
rag.ingest([
    Document(page_content="LangGraph enables stateful agent orchestration with checkpointing.")
])
results = rag.retrieve("What is LangGraph?")
print(results)
