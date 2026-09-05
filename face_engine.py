"""
Face Detection and Encoding Engine.
Detects faces from input images, computes face embeddings/descriptors,
and calculates visual similarity scores.

Backend priority (best accuracy -> worst, each one only used if the
previous one is unavailable or fails on a given image):

  1. InsightFace / ArcFace (buffalo_* RetinaFace detector + 512-d ArcFace
     embedding). Self-hosted ONNX model, ~99.7%+ LFW accuracy, installs
     from plain pip wheels (onnxruntime + insightface) with NO system
     compiler required. This is the primary, recommended backend.
  2. dlib / face_recognition (ResNet-1 + 128-d embedding, ~99.38% LFW).
     Requires dlib to be compiled from source (cmake + a C++ toolchain),
     which frequently fails to install in minimal/containerized
     environments. Used only if already installed.
  3. DeepFace (VGG-Face), if installed.
  4. Pixel-intensity fallback. This is NOT a face-recognition signal
     (it can match on lighting/background), so compute_similarity()
     hard-caps its confidence at 0.40 and never reports it as a
     verified identity match.

See README "Model Accuracy Notes" for benchmark numbers and the
self-hosted-model-vs-API tradeoff discussion.
"""

import os
import cv2
import numpy as np
from PIL import Image
import hashlib

# Module-level singletons so the (relatively large) ONNX models are loaded
# once per process instead of once per FaceEngine() instantiation.
_INSIGHTFACE_APP = None          # default: full-image detection, det_size=640
_INSIGHTFACE_APP_SMALL = None    # retry pass: tiny / pre-cropped face images
_INSIGHTFACE_LOAD_FAILED = False


def _get_insightface_app():
    """Lazily loads and caches the default InsightFace FaceAnalysis app."""
    global _INSIGHTFACE_APP, _INSIGHTFACE_LOAD_FAILED
    if _INSIGHTFACE_APP is not None or _INSIGHTFACE_LOAD_FAILED:
        return _INSIGHTFACE_APP
    try:
        from insightface.app import FaceAnalysis
        # buffalo_s: small (~130MB), CPU-friendly, RetinaFace detector +
        # ArcFace (w600k_mbf) 512-d recognition embedding.
        app = FaceAnalysis(name=os.getenv("INSIGHTFACE_MODEL", "buffalo_s"))
        app.prepare(ctx_id=int(os.getenv("INSIGHTFACE_CTX_ID", "-1")),
                    det_size=(640, 640))
        _INSIGHTFACE_APP = app
    except Exception as e:
        print(f"[FaceEngine] InsightFace unavailable, falling back: {e}")
        _INSIGHTFACE_LOAD_FAILED = True
        _INSIGHTFACE_APP = None
    return _INSIGHTFACE_APP


def _get_insightface_app_small():
    """
    Lazily loads a second InsightFace instance tuned for small / already
    tightly-cropped face images (e.g. 112x112 pre-aligned crops coming from
    another pipeline). The default det_size=640 detector frequently fails
    to find anything in these because there's no surrounding context --
    a smaller det_size + lower detection threshold recovers those cases.
    """
    global _INSIGHTFACE_APP_SMALL, _INSIGHTFACE_LOAD_FAILED
    if _INSIGHTFACE_APP_SMALL is not None or _INSIGHTFACE_LOAD_FAILED:
        return _INSIGHTFACE_APP_SMALL
    try:
        from insightface.app import FaceAnalysis
        app = FaceAnalysis(name=os.getenv("INSIGHTFACE_MODEL", "buffalo_s"))
        app.prepare(ctx_id=int(os.getenv("INSIGHTFACE_CTX_ID", "-1")),
                    det_size=(160, 160), det_thresh=0.3)
        _INSIGHTFACE_APP_SMALL = app
    except Exception:
        _INSIGHTFACE_APP_SMALL = None
    return _INSIGHTFACE_APP_SMALL


class FaceEngine:
    def __init__(self):
        # Load OpenCV Haar Cascade for Face Detection safely (last-resort fallback)
        self.face_cascade = None
        if hasattr(cv2, 'CascadeClassifier') and hasattr(cv2, 'data'):
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            if os.path.exists(cascade_path):
                self.face_cascade = cv2.CascadeClassifier(cascade_path)

        # ORB Feature Extractor for supplementary keypoint descriptors
        if hasattr(cv2, 'ORB_create'):
            self.orb = cv2.ORB_create(nfeatures=500)
        else:
            self.orb = None

        # Warm up InsightFace once (no-op if unavailable)
        self._insightface = _get_insightface_app()

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def _detect_from_array(self, img: np.ndarray):
        """
        Core multi-stage detector shared by detect_faces() and
        detect_faces_from_array(). Returns (bboxes, face_crops, insightface_faces)
        where insightface_faces[i] (if present) already carries a
        precomputed ArcFace embedding for that crop -- avoiding a second,
        redundant detection pass in encode_face().
        """
        bboxes, face_crops, if_faces = [], [], []

        # 1. InsightFace RetinaFace detector (most accurate, handles pose/scale well)
        app = self._insightface
        if app is not None:
            try:
                faces = app.get(img)
                if not faces:
                    small_app = _get_insightface_app_small()
                    if small_app is not None:
                        faces = small_app.get(img)
                for f in faces:
                    x1, y1, x2, y2 = [int(v) for v in f.bbox]
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(img.shape[1], x2), min(img.shape[0], y2)
                    if x2 <= x1 or y2 <= y1:
                        continue
                    bboxes.append((x1, y1, x2 - x1, y2 - y1))
                    face_crops.append(img[y1:y2, x1:x2])
                    if_faces.append(f)
            except Exception as e:
                print(f"[FaceEngine] InsightFace detection error: {e}")

        # 2. dlib / face_recognition (CNN model preferred; upsampled HOG fallback)
        if len(bboxes) == 0:
            try:
                import face_recognition
                rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                try:
                    face_locations = face_recognition.face_locations(rgb_img, model="cnn")
                except Exception:
                    face_locations = face_recognition.face_locations(
                        rgb_img, number_of_times_to_upsample=1, model="hog")
                for top, right, bottom, left in face_locations:
                    w, h = right - left, bottom - top
                    bboxes.append((int(left), int(top), int(w), int(h)))
                    face_crops.append(img[top:bottom, left:right])
                    if_faces.append(None)
            except Exception:
                pass

        # 3. OpenCV Haar Cascade if still nothing found
        if len(bboxes) == 0 and self.face_cascade is not None:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
            for (x, y, w, h) in faces:
                crop = img[y:y+h, x:x+w]
                face_crops.append(crop)
                bboxes.append((int(x), int(y), int(w), int(h)))
                if_faces.append(None)

        # 4. Explicit "no face found" fallback -- treat the whole image as a
        #    single unverified region rather than pretending a face exists.
        #    Callers can check encoding["vector_type"] == "Pixel Intensity Profile"
        #    combined with face_count/bbox to detect this case.
        if len(face_crops) == 0:
            h, w = img.shape[:2]
            face_crops.append(img)
            bboxes.append((0, 0, w, h))
            if_faces.append(None)

        return bboxes, face_crops, if_faces

    def detect_faces(self, image_path: str):
        """
        Detects faces using InsightFace (primary), dlib/face_recognition,
        and Haar cascades, in that order of preference.
        Returns bounding boxes [(x, y, w, h)] and cropped face images.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image file: {image_path}")

        bboxes, face_crops, _ = self._detect_from_array(img)
        return bboxes, face_crops

    def detect_faces_from_array(self, img: np.ndarray):
        """Detects faces directly from a numpy BGR image array."""
        if img is None or img.size == 0:
            return [], []
        bboxes, face_crops, _ = self._detect_from_array(img)
        return bboxes, face_crops

    # ------------------------------------------------------------------
    # Encoding
    # ------------------------------------------------------------------

    def encode_face(self, face_img: np.ndarray, insightface_face=None) -> dict:
        """
        Encodes a face crop into a feature vector descriptor, deep embedding
        vector, and cryptographic perceptual hash.

        `insightface_face` can be passed in when the caller already ran
        InsightFace detection on the full image (avoids re-detecting on the
        crop, which can fail for tight crops with little margin).
        """
        h_crop, w_crop = face_img.shape[:2]
        gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY) if len(face_img.shape) == 3 else face_img
        gray_resized = cv2.resize(gray, (128, 128))

        # Compute ORB descriptors if available (supplementary, not used for matching)
        keypoints, descriptors = None, None
        if self.orb is not None:
            keypoints, descriptors = self.orb.detectAndCompute(gray_resized, None)

        # 1. ArcFace 512-d embedding via InsightFace (best accuracy)
        arcface_embedding = None
        if insightface_face is not None and getattr(insightface_face, "normed_embedding", None) is not None:
            arcface_embedding = insightface_face.normed_embedding.tolist()
        else:
            app = self._insightface
            if app is not None:
                try:
                    faces = app.get(face_img)
                    if not faces:
                        # Retry with a detector tuned for small/pre-cropped
                        # face images (e.g. already-aligned 112x112 crops).
                        small_app = _get_insightface_app_small()
                        if small_app is not None:
                            faces = small_app.get(face_img)
                    if faces:
                        arcface_embedding = faces[0].normed_embedding.tolist()
                except Exception:
                    pass

        # 2. dlib ResNet 128-d embedding (only attempted if ArcFace unavailable)
        resnet_embedding = None
        if arcface_embedding is None:
            try:
                import face_recognition
                rgb_face = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
                known_loc = [(0, w_crop, h_crop, 0)]
                encs = face_recognition.face_encodings(rgb_face, known_face_locations=known_loc)
                if encs and len(encs) > 0:
                    resnet_embedding = encs[0].tolist()
            except Exception:
                pass

        # 3. DeepFace (VGG-Face) as a further fallback
        deep_embedding = None
        if arcface_embedding is None and resnet_embedding is None:
            try:
                from deepface import DeepFace
                embedding_objs = DeepFace.represent(img_path=face_img, model_name="VGG-Face", enforce_detection=False)
                if embedding_objs and len(embedding_objs) > 0:
                    deep_embedding = embedding_objs[0]["embedding"]
            except Exception:
                pass

        # Compute Perceptual / SHA-256 fingerprint of the normalized face
        face_bytes = gray_resized.tobytes()
        sha256_hash = hashlib.sha256(face_bytes).hexdigest()

        # Mean pixel intensity profile (last-resort embedding fallback --
        # NOT a real face-recognition signal, see compute_similarity())
        embedding_vector = cv2.resize(gray_resized, (16, 16)).flatten().astype(float)
        norm = np.linalg.norm(embedding_vector)
        if norm > 0:
            embedding_vector /= norm

        # Select highest-fidelity vector available:
        # ArcFace 512-d > dlib ResNet 128-d > DeepFace VGG > Pixel Profile
        if arcface_embedding is not None:
            final_embedding = arcface_embedding
            vector_type = "ArcFace-512d (InsightFace, ~99.7%+ LFW)"
        elif resnet_embedding is not None:
            final_embedding = resnet_embedding
            vector_type = "ResNet-128d (dlib, 99.38% LFW)"
        elif deep_embedding is not None:
            final_embedding = deep_embedding
            vector_type = "DeepFace (VGG-Face)"
        else:
            final_embedding = embedding_vector.tolist()
            vector_type = "Pixel Intensity Profile"

        return {
            "keypoints_count": len(keypoints) if keypoints else 0,
            "descriptors": descriptors.tolist() if descriptors is not None else [],
            "face_hash": sha256_hash,
            "embedding": final_embedding,
            "vector_type": vector_type,
            "is_deep_embedding": vector_type != "Pixel Intensity Profile",
            "dimensions": {"width": w_crop, "height": h_crop}
        }

    # ------------------------------------------------------------------
    # Similarity
    # ------------------------------------------------------------------

    def compute_similarity(self, encoding1: dict, encoding2: dict) -> float:
        """
        Computes similarity score (0.0 to 1.0) between two face encodings.
        Calibrated per-backend against each model's own published/standard
        decision threshold rather than a single generic formula.
        """
        vec1 = np.array(encoding1.get("embedding", []), dtype=float)
        vec2 = np.array(encoding2.get("embedding", []), dtype=float)
        if len(vec1) == 0 or len(vec2) == 0 or len(vec1) != len(vec2):
            return 0.0

        vtype1 = encoding1.get("vector_type", "")
        vtype2 = encoding2.get("vector_type", "")

        # Never compare two different backends' embeddings directly --
        # their vector spaces aren't compatible even if dimensions collide.
        if vtype1 != vtype2:
            return 0.0

        # Refuse to claim high similarity for Pixel Intensity Profile fallbacks
        # (these can match on lighting/background, not identity).
        if vtype1 == "Pixel Intensity Profile":
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            if norm1 == 0 or norm2 == 0:
                return 0.0
            pixel_sim = float((dot_product / (norm1 * norm2) + 1.0) / 2.0)
            return float(np.round(min(0.40, pixel_sim * 0.40), 4))

        if vtype1.startswith("ArcFace-512d"):
            # ArcFace embeddings from InsightFace are pre-L2-normalized, so
            # dot product == cosine similarity, in [-1, 1].
            # Standard buffalo_* verification threshold: cosine >= ~0.36 => same person.
            cosine_sim = float(np.dot(vec1, vec2))
            if cosine_sim >= 0.36:
                # Map [0.36, 1.0] -> [0.70, 1.0]
                similarity = 0.70 + (cosine_sim - 0.36) / 0.64 * 0.30
            else:
                # Map [-1.0, 0.36) -> [0.0, 0.70)
                similarity = max(0.0, (cosine_sim + 1.0) / 1.36 * 0.70)
            return float(np.round(min(1.0, similarity), 4))

        if vtype1.startswith("ResNet-128d"):
            # Euclidean distance for 128-d dlib embeddings.
            # Standard dlib threshold: dist < 0.6 => same person.
            euclidean_dist = float(np.linalg.norm(vec1 - vec2))
            if euclidean_dist < 0.6:
                similarity = 1.0 - (euclidean_dist / 0.6) * 0.30
            else:
                similarity = max(0.0, 0.70 - ((euclidean_dist - 0.6) / 0.4) * 0.70)
            return float(np.round(similarity, 4))

        # Cosine Similarity fallback for other deep embeddings (e.g. DeepFace)
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        cosine_sim = dot_product / (norm1 * norm2)
        similarity = (cosine_sim + 1.0) / 2.0
        return float(np.round(max(0.0, min(1.0, similarity)), 4))

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    def process_image(self, image_path: str) -> dict:
        """Full pipeline for face detection and encoding."""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image file: {image_path}")

        bboxes, face_crops, if_faces = self._detect_from_array(img)
        encodings = [self.encode_face(face_crops[i], insightface_face=if_faces[i])
                     for i in range(len(face_crops))]

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
