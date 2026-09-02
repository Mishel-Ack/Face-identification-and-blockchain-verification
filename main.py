"""
Main Execution Script for Face Identification & Blockchain Verification Pipeline.

Usage:
  python main.py --input <path_to_face_image> [--keywords "<search_keywords>"]
"""

import argparse
import json
import os
import sys

from face_engine import FaceEngine
from web_search import WebSearchEngine
from blockchain_verifier import BlockchainVerifier

def run_pipeline(image_path: str, search_keywords: str = "face identification social media profile") -> dict:
    print("\n=======================================================")
    print("  FACE IDENTIFICATION & BLOCKCHAIN VERIFICATION PIPELINE")
    print("=======================================================\n")

    if not os.path.exists(image_path):
        print(f"Error: Input image file '{image_path}' does not exist.")
        sys.exit(1)

    # 1. Face Identification Step
    print(f"[*] STEP 1: Processing face input image: {image_path}")
    face_engine = FaceEngine()
    face_data = face_engine.process_image(image_path)
    
    print(f"    -> Image SHA-256 Hash: {face_data['image_hash'][:16]}...")
    print(f"    -> Detected {face_data['face_count']} face(s) in image.")
    for i, face in enumerate(face_data["faces"]):
        bbox = face["bbox"]
        print(f"       Face #{i+1}: Bounding Box = ({bbox[0]}, {bbox[1]}, {bbox[2]}, {bbox[3]})")
        print(f"       Face #{i+1} Perceptual Hash = {face['encoding']['face_hash'][:16]}...")

    # 2. Web / Social Media Search Step
    print(f"\n[*] STEP 2: Searching web & social media for matching content...")
    search_engine = WebSearchEngine()
    search_result = search_engine.find_matching_post(face_data, query_keywords=search_keywords)
    
    post = search_result["post_metadata"]
    print(f"    -> Found Match on Platform: {post['platform']}")
    print(f"    -> URL: {post['url']}")
    print(f"    -> Author: {post['author']}")
    print(f"    -> Title: {post['title']}")
    print(f"    -> Match Confidence: {search_result['match_confidence'] * 100:.1f}%")
    print(f"    -> Content Fingerprint: {search_result['content_fingerprint']}")

    # 3. Blockchain Verification & Anchor Step
    print(f"\n[*] STEP 3: Registering & Anchoring record to Blockchain...")
    verifier = BlockchainVerifier(ledger_db_path="blockchain_ledger.json")
    tx_record = verifier.record_verification(face_data, search_result)

    print(f"    -> Transaction Status: {tx_record['status']}")
    print(f"    -> Transaction Hash (TxHash): {tx_record['transaction_hash']}")
    print(f"    -> Block Index: #{tx_record['block_index']}")
    print(f"    -> Block Hash: {tx_record['block_hash']}")
    print(f"    -> Network: {tx_record['network']}")

    # 4. Immediate Integrity Self-Verification
    print(f"\n[*] STEP 4: Performing immediate on-chain self-verification...")
    is_valid, verify_details = verifier.verify_on_chain_record(
        tx_record["transaction_hash"],
        expected_content_fingerprint=search_result["content_fingerprint"]
    )

    if is_valid:
        print("    -> [SUCCESS] On-chain verification PASSED! Data is authentic & tamper-evident.")
    else:
        print(f"    -> [FAILED] On-chain verification failed: {verify_details.get('error')}")

    print("\n=======================================================")
    print("                PIPELINE COMPLETE")
    print("=======================================================\n")

    return {
        "face_data": face_data,
        "search_result": search_result,
        "tx_record": tx_record,
        "verification_result": verify_details
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Face Identification & Blockchain Verification Pipeline")
    parser.add_argument("--input", "-i", type=str, required=True, help="Path to input face image")
    parser.add_argument("--keywords", "-k", type=str, default="face identification profile social media", help="Search keywords for web query")
    
    args = parser.parse_args()
    run_pipeline(args.input, args.keywords)
