import time
from typing import List, Optional, Tuple

import numpy as np


class AVX2VectorOperations:
    """
    AVX2 optimized vector operations for context embeddings
    NumPy automatically uses SIMD instructions when available
    """

    @staticmethod
    def cosine_similarity_batch(
        query_vector: np.ndarray, vectors: np.ndarray
    ) -> np.ndarray:
        """
        Compute cosine similarity using AVX2 optimized operations

        Args:
            query_vector: Shape (512,)
            vectors: Shape (n, 512)

        Returns:
            Similarities shape (n,)
        """
        # Normalize vectors (NumPy uses AVX2 for these operations)
        query_norm = query_vector / np.linalg.norm(query_vector)
        vectors_norm = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

        # Dot product (highly optimized with AVX2)
        similarities = np.dot(vectors_norm, query_norm)

        return similarities

    @staticmethod
    def find_top_k_similar(
        query_vector: np.ndarray, vectors: np.ndarray, k: int = 10
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Find top-k most similar vectors using AVX2 optimization

        Returns:
            (indices, similarities) of top-k matches
        """
        similarities = AVX2VectorOperations.cosine_similarity_batch(
            query_vector, vectors
        )

        # Partial sort for top-k (optimized)
        top_k_indices = np.argpartition(similarities, -k)[-k:]
        top_k_indices = top_k_indices[np.argsort(similarities[top_k_indices])[::-1]]

        return top_k_indices, similarities[top_k_indices]

    @staticmethod
    def benchmark_avx2():
        """Benchmark AVX2 operations"""
        # Create test data
        query = np.random.randn(512).astype(np.float32)
        vectors = np.random.randn(10000, 512).astype(np.float32)

        # Benchmark
        start = time.time()
        indices, scores = AVX2VectorOperations.find_top_k_similar(query, vectors, k=100)
        elapsed = time.time() - start

        print(f"AVX2 Vector Operations Benchmark:")
        print(f"  - Vectors processed: 10,000")
        print(f"  - Dimensions: 512")
        print(f"  - Time: {elapsed*1000:.2f}ms")
        print(f"  - Throughput: {10000/elapsed:.0f} vectors/sec")

        return elapsed


if __name__ == "__main__":
    ops = AVX2VectorOperations()
    ops.benchmark_avx2()
