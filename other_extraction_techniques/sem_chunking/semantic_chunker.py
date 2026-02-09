import numpy as np
from typing import List, Optional
from sentence_transformers import SentenceTransformer
import re


class SemanticChunker:
    """
    Class that takes a piece of text and returns a split of it based on the content using semantic chunking.
    It receives all the thresholds and parameters and other info (if needed) and returns the chunked text.
    
    This implementation uses sentence embeddings to measure semantic similarity between consecutive
    sentences and creates chunk boundaries when the similarity drops below a threshold.
    """
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        similarity_threshold: float = 0.5,
        min_chunk_size: int = 1,
        max_chunk_size: int = 10,
        use_percentile: bool = True,
        percentile_threshold: float = 25.0
    ) -> None:
        """
        Initialize the semantic chunker.
        
        Args:
            model_name: Name of the sentence transformer model to use for embeddings
            similarity_threshold: Threshold for semantic similarity (0-1). Lower values create more chunks.
            min_chunk_size: Minimum number of sentences per chunk
            max_chunk_size: Maximum number of sentences per chunk
            use_percentile: If True, use percentile-based thresholding instead of fixed threshold
            percentile_threshold: Percentile value for dynamic thresholding (0-100)
        """
        self.model = SentenceTransformer(model_name)
        self.similarity_threshold = similarity_threshold
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.use_percentile = use_percentile
        self.percentile_threshold = percentile_threshold
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into semantic chunks based on content similarity.
        
        Args:
            text: Input text to be chunked
            
        Returns:
            List of text chunks
        """
        # Split text into sentences
        sentences = self._split_into_sentences(text)
        
        if len(sentences) <= 1:
            return [text]
        
        # Generate embeddings for all sentences
        embeddings = self.model.encode(sentences, convert_to_numpy=True)
        
        # Calculate similarities between consecutive sentences
        similarities = self._calculate_consecutive_similarities(embeddings)
        
        # Determine chunk boundaries based on similarity drops
        boundaries = self._find_chunk_boundaries(similarities, len(sentences))
        
        # Create chunks from boundaries
        chunks = self._create_chunks(sentences, boundaries)
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences using regex patterns.
        
        Args:
            text: Input text
            
        Returns:
            List of sentences
        """
        # Pattern to split on sentence boundaries
        # Handles periods, question marks, exclamation marks followed by space or newline
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])\n+'
        
        sentences = re.split(sentence_pattern, text)
        
        # Clean up sentences
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _calculate_consecutive_similarities(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Calculate cosine similarity between consecutive sentence embeddings.
        
        Args:
            embeddings: Array of sentence embeddings
            
        Returns:
            Array of similarity scores
        """
        similarities = []
        
        for i in range(len(embeddings) - 1):
            # Cosine similarity between consecutive embeddings
            similarity = np.dot(embeddings[i], embeddings[i + 1]) / (
                np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[i + 1])
            )
            similarities.append(similarity)
        
        return np.array(similarities)
    
    def _find_chunk_boundaries(self, similarities: np.ndarray, num_sentences: int) -> List[int]:
        """
        Find chunk boundaries based on similarity scores.
        
        Args:
            similarities: Array of similarity scores between consecutive sentences
            num_sentences: Total number of sentences
            
        Returns:
            List of boundary indices (sentence positions where chunks should split)
        """
        boundaries = [0]  # Start with the first sentence
        
        if len(similarities) == 0:
            boundaries.append(num_sentences)
            return boundaries
        
        # Determine threshold
        if self.use_percentile:
            threshold = np.percentile(similarities, self.percentile_threshold)
        else:
            threshold = self.similarity_threshold
        
        current_chunk_size = 1
        
        for i, similarity in enumerate(similarities):
            current_chunk_size += 1
            
            # Create boundary if:
            # 1. Similarity drops below threshold AND
            # 2. Current chunk meets minimum size AND
            # 3. We haven't exceeded maximum chunk size
            if similarity < threshold and current_chunk_size >= self.min_chunk_size:
                boundaries.append(i + 1)
                current_chunk_size = 0
            elif current_chunk_size >= self.max_chunk_size:
                # Force boundary if max chunk size reached
                boundaries.append(i + 1)
                current_chunk_size = 0
        
        # Add final boundary
        if boundaries[-1] != num_sentences:
            boundaries.append(num_sentences)
        
        return boundaries
    
    def _create_chunks(self, sentences: List[str], boundaries: List[int]) -> List[str]:
        """
        Create text chunks from sentences and boundary indices.
        
        Args:
            sentences: List of sentences
            boundaries: List of boundary indices
            
        Returns:
            List of text chunks
        """
        chunks = []
        
        for i in range(len(boundaries) - 1):
            start_idx = boundaries[i]
            end_idx = boundaries[i + 1]
            
            # Join sentences in this chunk
            chunk = ' '.join(sentences[start_idx:end_idx])
            chunks.append(chunk)
        
        return chunks
    
    def chunk_text_with_metadata(self, text: str) -> List[dict]:
        """
        Split text into semantic chunks and return with metadata.
        
        Args:
            text: Input text to be chunked
            
        Returns:
            List of dictionaries containing chunk text and metadata
        """
        sentences = self._split_into_sentences(text)
        
        if len(sentences) <= 1:
            return [{
                'text': text,
                'start_sentence': 0,
                'end_sentence': len(sentences),
                'num_sentences': len(sentences)
            }]
        
        embeddings = self.model.encode(sentences, convert_to_numpy=True)
        similarities = self._calculate_consecutive_similarities(embeddings)
        boundaries = self._find_chunk_boundaries(similarities, len(sentences))
        
        chunks_with_metadata = []
        
        for i in range(len(boundaries) - 1):
            start_idx = boundaries[i]
            end_idx = boundaries[i + 1]
            
            chunk_text = ' '.join(sentences[start_idx:end_idx])
            
            chunks_with_metadata.append({
                'text': chunk_text,
                'start_sentence': start_idx,
                'end_sentence': end_idx,
                'num_sentences': end_idx - start_idx
            })
        
        return chunks_with_metadata