import re
import numpy as np
import tiktoken
import logging
from typing import List, Dict, Any, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Use try-except for app imports to allow usage in different contexts
try:
    from app.config import settings
    from app.ingestion.embedder import get_embeddings
except ImportError:
    # Fallback/Mock for testing or if imports fail
    settings = Any
    def get_embeddings(texts: List[str]) -> List[List[float]]:
        return [[0.0] * 1536 for _ in texts]

logger = logging.getLogger("rag.ingestion.semantic_splitter")

class SemanticSplitter:
    """
    Semantic Chunking Splitter.
    Splits text by sentences and groups them based on cosine similarity of embeddings.
    Falls back to recursive character splitting if a chunk exceeds the token limit.
    """

    def __init__(
        self,
        threshold: float = 0.8,
        max_tokens: int = 1000,
        model_name: str = "gpt-4o-mini",
    ):
        self.threshold = threshold
        self.max_tokens = max_tokens
        try:
            self.tokenizer = tiktoken.encoding_for_model(model_name)
        except Exception:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
            
        self.fallback_splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_tokens,
            chunk_overlap=min(max_tokens // 10, 50),
            length_function=self._count_tokens
        )

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        return len(self.tokenizer.encode(text))

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using regex."""
        # Split on . ! ? followed by whitespace or end of string.
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        a = np.array(v1)
        b = np.array(v2)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return np.dot(a, b) / (norm_a * norm_b)

    def split_text(self, text: str) -> List[str]:
        """Split text semantically based on topic changes."""
        if not text:
            return []
            
        sentences = self._split_into_sentences(text)
        if not sentences:
            return []
        
        if len(sentences) == 1:
            return self._process_chunk(sentences[0])

        # Batch embed all sentences for efficiency
        embeddings = get_embeddings(sentences)
        
        chunks = []
        current_chunk_sentences = [sentences[0]]
        
        for i in range(1, len(sentences)):
            # Calculate similarity between current sentence and previous one
            similarity = self._cosine_similarity(embeddings[i-1], embeddings[i])
            
            # If similarity is below threshold, it's a topic change
            if similarity < self.threshold:
                chunk_text = " ".join(current_chunk_sentences)
                chunks.extend(self._process_chunk(chunk_text))
                current_chunk_sentences = [sentences[i]]
            else:
                current_chunk_sentences.append(sentences[i])
        
        # Add the remaining sentences as the final chunk
        if current_chunk_sentences:
            chunk_text = " ".join(current_chunk_sentences)
            chunks.extend(self._process_chunk(chunk_text))
            
        return chunks

    def _process_chunk(self, text: str) -> List[str]:
        """Check if chunk exceeds token limit and apply fallback if necessary."""
        if self._count_tokens(text) > self.max_tokens:
            logger.info(f"Semantic chunk too large ({self._count_tokens(text)} tokens). Applying recursive fallback.")
            return self.fallback_splitter.split_text(text)
        return [text]

    def split_documents(self, documents: List[Any]) -> List[Dict[str, Any]]:
        """
        Main entry point for document chunking.
        Returns a list of dicts compatible with the ingestion pipeline.
        """
        all_chunks: List[Dict[str, Any]] = []
        chunk_counter = 0
        
        def _slugify(text: str) -> str:
            slug = re.sub(r"[^\w\s-]", "", text.lower())
            return re.sub(r"[\s-]+", "_", slug).strip("_")

        for doc in documents:
            source_slug = _slugify(doc.source)
            text = doc.page_content
            if not text:
                continue
                
            chunk_texts = self.split_text(text)
            
            for chunk_text in chunk_texts:
                chunk_counter += 1
                all_chunks.append({
                    "chunk_id": f"{source_slug}_chunk_{chunk_counter}",
                    "source": doc.source,
                    "content": chunk_text,
                    "page": doc.page,
                })
                
        return all_chunks
