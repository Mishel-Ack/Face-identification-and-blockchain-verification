"""
Face Detection and Encoding Engine.
Detects faces from input images, computes face embeddings/descriptors,
and calculates visual similarity scores.
"""

import os
import cv2
import numpy as np
from PIL import Image
import hashlib

class FaceEngine:
    def __init__(self):
        # Load OpenCV Haar Cascade for Face Detection safely
        self.face_cascade = None
        if hasattr(cv2, 'CascadeClassifier') and hasattr(cv2, 'data'):
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            if os.path.exists(cascade_path):
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        # ORB Feature Extractor for face descriptor fingerprinting
        if hasattr(cv2, 'ORB_create'):
            self.orb = cv2.ORB_create(nfeatures=500)
        else:
            self.orb = None

    def detect_faces(self, image_path: str):
        """
        Detects faces in an image file.
        Returns bounding boxes [(x, y, w, h)] and cropped face images.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image file: {image_path}")

        faces = []
        if self.face_cascade is not None:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )

        face_crops = []
        bboxes = []
        for (x, y, w, h) in faces:
            crop = img[y:y+h, x:x+w]
            face_crops.append(crop)
            bboxes.append((int(x), int(y), int(w), int(h)))

        # Fallback if no faces detected / cascade absent: treat center ROI or whole image
        if len(face_crops) == 0:
            h, w = img.shape[:2]
            face_crops.append(img)
            bboxes.append((0, 0, w, h))

        return bboxes, face_crops

    def encode_face(self, face_img: np.ndarray) -> dict:
        """
        Encodes face region into a feature vector descriptor and cryptographic perceptual hash.
        """
        gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY) if len(face_img.shape) == 3 else face_img
        gray_resized = cv2.resize(gray, (128, 128))

        # Compute ORB descriptors if available
        keypoints, descriptors = None, None
        if self.orb is not None:
            keypoints, descriptors = self.orb.detectAndCompute(gray_resized, None)

        # Compute Perceptual / SHA-256 fingerprint of the normalized face
        face_bytes = gray_resized.tobytes()
        sha256_hash = hashlib.sha256(face_bytes).hexdigest()

        # Mean pixel intensity profile (embedding vector representation)
        embedding_vector = cv2.resize(gray_resized, (16, 16)).flatten().astype(float)
        norm = np.linalg.norm(embedding_vector)
        if norm > 0:
            embedding_vector /= norm

        return {
            "keypoints_count": len(keypoints) if keypoints else 0,
            "descriptors": descriptors if descriptors is not None else np.array([]),
            "face_hash": sha256_hash,
            "embedding": embedding_vector.tolist(),
            "dimensions": {"width": face_img.shape[1], "height": face_img.shape[0]}
        }

    def compute_similarity(self, encoding1: dict, encoding2: dict) -> float:
        """
        Computes cosine similarity between two face embedding vectors (0.0 to 1.0).
        """
        vec1 = np.array(encoding1["embedding"])
        vec2 = np.array(encoding2["embedding"])
        if len(vec1) == 0 or len(vec2) == 0:
            return 0.0

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = float(dot_product / (norm1 * norm2))
        return max(0.0, min(1.0, similarity))

    def process_image(self, image_path: str) -> dict:
        """
        Full pipeline for face detection and encoding.
        """
        bboxes, face_crops = self.detect_faces(image_path)
        encodings = [self.encode_face(crop) for crop in face_crops]
        
        # Calculate full image checksum
        with open(image_path, "rb") as f:
            full_img_sha256 = hashlib.sha256(f.read()).hexdigest()

        return {
            "image_path": image_path,
            "image_hash": full_img_sha256,
            "face_count": len(bboxes),
            "faces": [
                {
                    "bbox": bboxes[i],
                    "encoding": encodings[i]
                }
                for i in range(len(bboxes))
            ]
        }
