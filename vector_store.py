"""
Vector Database Store for Scalable Face Identification (FAISS / NearestNeighbors).
Enables sub-millisecond approximate nearest neighbor search across thousands/millions of faces.
"""

import os
import json
import numpy as np
from typing import List, Dict, Any, Tuple

class FaceVectorStore:
    def __init__(self, index_file_path: str = "face_vector_index.json"):
        self.index_file_path = index_file_path
        self.vectors = []  # list of dicts: {"id": str, "metadata": dict, "embedding": list}
        self.use_faiss = False
        self._faiss_index = None

        # Check if faiss is installed
        try:
            import faiss
            self.use_faiss = True
        except ImportError:
            self.use_faiss = False

        self._load_store()

    def _load_store(self):
        """Loads vector index from persistent storage."""
        if os.path.exists(self.index_file_path):
            try:
                with open(self.index_file_path, "r") as f:
                    self.vectors = json.load(f)
                self._rebuild_index()
            except Exception as e:
                print(f"[FaceVectorStore] Warning loading store: {e}")
                self.vectors = []

    def _save_store(self):
        """Saves vector records to JSON persistence."""
        with open(self.index_file_path, "w") as f:
            json.dump(self.vectors, f, indent=2)

    def _rebuild_index(self):
        """Rebuilds internal FAISS index if available."""
        if not self.use_faiss or not self.vectors:
            return

        try:
            import faiss
            embeddings = [v["embedding"] for v in self.vectors]
            dim = len(embeddings[0])
            np_embeddings = np.array(embeddings, dtype=np.float32)
            
            # Use IndexFlatIP (Inner Product on normalized vectors = Cosine Similarity)
            faiss.normalize_L2(np_embeddings)
            self._faiss_index = faiss.IndexFlatIP(dim)
            self._faiss_index.add(np_embeddings)
        except Exception as e:
            print(f"[FaceVectorStore] FAISS index rebuild warning: {e}")
            self._faiss_index = None

    def add_face_vector(self, face_id: str, embedding: List[float], metadata: dict) -> bool:
        """Adds a face vector embedding to the index."""
        if not embedding:
            return False

        # Remove existing if face_id exists
        self.vectors = [v for v in self.vectors if v["id"] != face_id]

        record = {
            "id": face_id,
            "embedding": embedding,
            "metadata": metadata
        }
        self.vectors.append(record)
        self._save_store()
        self._rebuild_index()
        return True

    def search_knn(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Performs Fast K-Nearest Neighbors search.
        Returns top_k matching records with similarity scores.
        """
        if not self.vectors or not query_embedding:
            return []

        q_vec = np.array(query_embedding, dtype=np.float32)
        dim = len(q_vec)

        # Filter candidates by matching vector dimension
        valid_candidates = [v for v in self.vectors if len(v["embedding"]) == dim]
        if not valid_candidates:
            return []

        if self.use_faiss and self._faiss_index is not None and self._faiss_index.ntotal == len(valid_candidates):
            try:
                import faiss
                q_arr = np.array([query_embedding], dtype=np.float32)
                faiss.normalize_L2(q_arr)
                distances, indices = self._faiss_index.search(q_arr, min(top_k, len(valid_candidates)))
                
                results = []
                for score, idx in zip(distances[0], indices[0]):
                    if idx != -1 and idx < len(valid_candidates):
                        item = valid_candidates[idx]
                        results.append({
                            "id": item["id"],
                            "metadata": item["metadata"],
                            "similarity_score": float(np.round(score, 4))
                        })
                return results
            except Exception:
                pass

        # NumPy Cosine Similarity fallback
        cand_matrix = np.array([v["embedding"] for v in valid_candidates], dtype=float)
        norm_q = np.linalg.norm(q_vec)
        norm_matrix = np.linalg.norm(cand_matrix, axis=1)

        if norm_q == 0:
            return []

        valid_mask = norm_matrix > 0
        if not np.any(valid_mask):
            return []

        dot_products = np.dot(cand_matrix[valid_mask], q_vec)
        cosine_sims = dot_products / (norm_matrix[valid_mask] * norm_q)

        valid_indices = np.where(valid_mask)[0]
        sorted_order = np.argsort(cosine_sims)[::-1][:top_k]

        results = []
        for idx in sorted_order:
            orig_idx = valid_indices[idx]
            sim = float(np.round((cosine_sims[idx] + 1.0) / 2.0, 4))
            item = valid_candidates[orig_idx]
            results.append({
                "id": item["id"],
                "metadata": item["metadata"],
                "similarity_score": sim
            })

        return results
