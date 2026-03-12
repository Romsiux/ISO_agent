"""
RAG Engine
==========
Handles document ingestion, chunking, embedding into ChromaDB,
and retrieval via LangChain's MultiQueryRetriever (query translation).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple

from langchain.retrievers import MultiQueryRetriever
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.document_loaders import (
    Docx2txtLoader,
    PyPDFLoader,
    TextLoader,
)
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI

from config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    CHROMA_PERSIST_DIR,
    COLLECTION_NAME,
    TOP_K_RESULTS,
)

logger = logging.getLogger(__name__)


class RAGEngine:
    """
    Encapsulates the full RAG pipeline:
      1. Load PDFs / DOCX / TXT files and split into chunks
      2. Embed chunks with a local HuggingFace model and persist in ChromaDB
      3. Retrieve via MultiQueryRetriever (generates multiple query variants
         to improve recall — this is the "query translation" technique)
    """

    def __init__(self, openai_api_key: str) -> None:
        self.api_key = openai_api_key
        # Local embeddings — no OpenAI API key needed for indexing
        self.embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2"
        )
        self.vectorstore: Optional[Chroma] = None
        self.retriever: Optional[MultiQueryRetriever] = None
        self._try_load_existing()

    # ── Setup helpers ─────────────────────────────────────────────────────────

    def _try_load_existing(self) -> int:
        """Load an existing ChromaDB if it already contains chunks."""
        if not Path(CHROMA_PERSIST_DIR).exists():
            return 0
        try:
            vs = Chroma(
                collection_name=COLLECTION_NAME,
                embedding_function=self.embeddings,
                persist_directory=CHROMA_PERSIST_DIR,
            )
            count = vs._collection.count()
            if count > 0:
                self.vectorstore = vs
                self._setup_retriever()
                logger.info("Loaded existing vectorstore (%d chunks)", count)
                return count
        except Exception as exc:
            logger.warning("Could not load existing vectorstore: %s", exc)
        return 0

    def _setup_retriever(self) -> None:
        """
        Wrap the base similarity retriever with MultiQueryRetriever.

        MultiQueryRetriever asks the LLM to rephrase the user's question
        into several alternative queries, then merges the retrieved docs.
        This reduces missed results caused by wording mismatches.
        """
        query_llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            openai_api_key=self.api_key,
        )
        base = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": TOP_K_RESULTS},
        )
        self.retriever = MultiQueryRetriever.from_llm(
            retriever=base,
            llm=query_llm,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def load_documents(self, file_paths: List[str]) -> Tuple[int, List[str]]:
        """
        Ingest a list of file paths into the vector store.

        Returns
        -------
        (chunks_added, error_messages)
        """
        all_docs: List[Document] = []
        errors: List[str] = []

        for fp in file_paths:
            try:
                docs = self._load_file(fp)
                all_docs.extend(docs)
                logger.info("Loaded %d pages from %s", len(docs), fp)
            except Exception as exc:
                msg = f"Error loading {Path(fp).name}: {exc}"
                errors.append(msg)
                logger.error(msg)

        if not all_docs:
            return 0, errors

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks = splitter.split_documents(all_docs)

        if self.vectorstore is None:
            self.vectorstore = Chroma(
                collection_name=COLLECTION_NAME,
                embedding_function=self.embeddings,
                persist_directory=CHROMA_PERSIST_DIR,
            )

        self.vectorstore.add_documents(chunks)
        self._setup_retriever()
        logger.info("Indexed %d chunks", len(chunks))
        return len(chunks), errors

    def retrieve(self, query: str) -> List[Document]:
        """Return relevant documents for *query*."""
        if self.retriever is None:
            return []
        try:
            return self.retriever.invoke(query)
        except Exception as exc:
            logger.error("Retrieval error: %s", exc)
            return []

    def get_chunk_count(self) -> int:
        """Number of chunks currently stored."""
        if self.vectorstore is None:
            return 0
        try:
            return self.vectorstore._collection.count()
        except Exception:
            return 0

    def clear(self) -> None:
        """Wipe the entire vector store."""
        if self.vectorstore:
            self.vectorstore.delete_collection()
        self.vectorstore = None
        self.retriever = None

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _load_file(file_path: str) -> List[Document]:
        ext = Path(file_path).suffix.lower()
        if ext == ".pdf":
            return PyPDFLoader(file_path).load()
        if ext in {".docx", ".doc"}:
            return Docx2txtLoader(file_path).load()
        if ext == ".txt":
            return TextLoader(file_path, encoding="utf-8").load()
        raise ValueError(f"Unsupported file type: {ext}")