"""
Unit & Integration Test Suite for Face Identification & Blockchain Verification Pipeline.
"""

import pytest
import os
import tempfile
import cv2
import numpy as np

from face_engine import FaceEngine
from web_search import WebSearchEngine
from blockchain_verifier import BlockchainVerifier
from main import run_pipeline

@pytest.fixture
def sample_image():
    """Creates a temporary synthetic face-like test image."""
    fd, path = tempfile.mkstemp(suffix=".jpg")
    os.close(fd)
    
    # Create a 200x200 RGB image with a circle drawn (simulating a face shape)
    img = np.ones((200, 200, 3), dtype=np.uint8) * 240
    cv2.circle(img, (100, 100), 50, (100, 150, 200), -1)  # Head
    cv2.circle(img, (80, 85), 8, (50, 50, 50), -1)      # Left eye
    cv2.circle(img, (120, 85), 8, (50, 50, 50), -1)     # Right eye
    cv2.ellipse(img, (100, 125), (20, 10), 0, 0, 180, (50, 50, 50), 3) # Mouth

    cv2.imwrite(path, img)
    yield path
    
    if os.path.exists(path):
        os.remove(path)

def test_face_detection_and_encoding(sample_image):
    engine = FaceEngine()
    face_data = engine.process_image(sample_image)

    assert face_data is not None
    assert "image_hash" in face_data
    assert face_data["face_count"] >= 1
    assert len(face_data["faces"]) >= 1

    encoding = face_data["faces"][0]["encoding"]
    assert "face_hash" in encoding
    assert "embedding" in encoding

def test_web_search():
    search_engine = WebSearchEngine()
    fake_face_data = {"image_hash": "a1b2c3d4e5f67890123456789abcdef0"}
    
    result = search_engine.find_matching_post(fake_face_data, query_keywords="ai developer profile")

    assert result["matched"] is True
    assert "post_metadata" in result
    assert "content_fingerprint" in result
    assert result["post_metadata"]["url"].startswith("http")

def test_blockchain_verification(sample_image):
    ledger_path = tempfile.mktemp(suffix=".json")
    verifier = BlockchainVerifier(ledger_db_path=ledger_path)

    face_engine = FaceEngine()
    face_data = face_engine.process_image(sample_image)

    search_engine = WebSearchEngine()
    search_result = search_engine.find_matching_post(face_data)

    tx_record = verifier.record_verification(face_data, search_result)

    assert tx_record["status"] == "CONFIRMED_ON_CHAIN"
    assert tx_record["transaction_hash"].startswith("0x")
    assert tx_record["block_index"] >= 1

    # Verify on chain
    is_valid, details = verifier.verify_on_chain_record(
        tx_record["transaction_hash"],
        expected_content_fingerprint=search_result["content_fingerprint"]
    )
    assert is_valid is True
    assert details["valid"] is True

    # Test Tamper Detection
    is_valid_tampered, tamper_details = verifier.verify_on_chain_record(
        tx_record["transaction_hash"],
        expected_content_fingerprint="INVALID_TAMPERED_FINGERPRINT"
    )
    assert is_valid_tampered is False
    assert "Fingerprint mismatch" in tamper_details["error"]

    if os.path.exists(ledger_path):
        os.remove(ledger_path)

def test_full_pipeline(sample_image):
    results = run_pipeline(sample_image, "test face query")

    assert "face_data" in results
    assert "search_result" in results
    assert "tx_record" in results
    assert results["tx_record"]["status"] == "CONFIRMED_ON_CHAIN"
