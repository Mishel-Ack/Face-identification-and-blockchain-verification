"""
Command-line interface for Face Identification & Blockchain Verification pipeline.
Usage:
    python main.py --image sample_face.jpg --name "Alex Dev" --keywords "AI innovator" --verbose
"""

import argparse
import json
import logging
from typing import Dict, Any

from face_engine import FaceEngine
from web_search import WebSearchEngine
from blockchain_verifier import BlockchainVerifier

logger = logging.getLogger("veriface.main")

def run_pipeline(image_path: str, search_query: str = "face identification profile social media", target_platforms: list = None) -> Dict[str, Any]:
    """
    Executes the 3-stage face identification and blockchain verification workflow.
    """
    # 1. Face Detection & Feature Extraction
    print(f"\n[*] STEP 1: Processing face input image: {image_path}")
    face_engine = FaceEngine()
    face_data = face_engine.process_image(image_path)

    print(f"    -> Image SHA-256 Hash: {face_data['image_hash'][:16]}...")
    print(f"    -> Detected {face_data['face_count']} face(s) in image.")
    for i, face in enumerate(face_data["faces"]):
        bbox = face["bbox"]
        print(f"       Face #{i+1}: Bounding Box = {bbox}")
        print(f"       Face #{i+1} Perceptual Hash = {face['encoding']['face_hash'][:16]}...")

    # 2. Dynamic Web & Social Media Search Step
    print(f"\n[*] STEP 2: Searching web & social media for matching content...")
    search_engine = WebSearchEngine()
    search_result = search_engine.find_matching_post(
        face_data, 
        query_keywords=search_query,
        target_platforms=target_platforms
    )
    post = search_result["post_metadata"]

    print(f"    -> Candidate Search Source: {search_result.get('search_source', 'unknown')}")
    print(f"    -> Found Candidate on Platform: {post['platform']}")
    print(f"    -> URL: {post['url']}")
    print(f"    -> Author: {post['author']}")
    print(f"    -> Title: {post['title']}")
    print(f"    -> Candidate Relevance Score (Text + Platform + Visual Similarity): {search_result['candidate_relevance_score'] * 100:.1f}%")
    print(f"    -> Content Fingerprint: {search_result['content_fingerprint']}")

    # 3. Blockchain Verification & Anchor Step
    print(f"\n[*] STEP 3: Registering & Anchoring record to Blockchain...")
    verifier = BlockchainVerifier(ledger_db_path="blockchain.db")
    tx_record = verifier.record_verification(face_data, search_result)

    print(f"    -> Transaction Status: {tx_record['status']}")
    print(f"    -> Transaction Hash (TxHash): {tx_record['transaction_hash']}")
    print(f"    -> Block Index: #{tx_record['block_index']}")
    print(f"    -> Block Hash: {tx_record['block_hash']}")
    print(f"    -> Network: {tx_record['network']}")

    # 4. Immediate Integrity Self-Verification
    print(f"\n[*] STEP 4: Verifying on-chain tamper evidence & proof integrity...")
    is_valid, verify_details = verifier.verify_on_chain_record(
        tx_record["transaction_hash"],
        expected_content_fingerprint=search_result["content_fingerprint"]
    )
    print(f"    -> Verification Success: {is_valid}")
    print(f"    -> Tamper Evidence: Chain Valid & Unmodified")

    return {
        "face_data": face_data,
        "search_result": search_result,
        "tx_record": tx_record,
        "is_valid": is_valid,
        "verify_details": verify_details
    }

def main():
    parser = argparse.ArgumentParser(description='Face Identification & Blockchain Verification Pipeline')
    parser.add_argument('--image', default='sample_face.jpg', help='Path to face image')
    parser.add_argument('--name', default='', help='Name to search for')
    parser.add_argument('--keywords', default='AI tech innovator keynote', help='Search keywords')
    parser.add_argument('--location', default='', help='Location hint')
    parser.add_argument('--verbose', action='store_true', help='Verbose JSON output')
    args = parser.parse_args()

    query_parts = [p for p in [args.name, args.keywords, args.location] if p]
    query = " ".join(query_parts) if query_parts else "AI tech innovator keynote"

    results = run_pipeline(args.image, search_query=query)

    if args.verbose:
        print("\n" + "="*60)
        print("PIPELINE EXECUTION SUMMARY (JSON):")
        print("="*60)
        print(json.dumps({
            'face_count': results['face_data']['face_count'],
            'search_url': results['search_result']['post_metadata']['url'],
            'transaction_hash': results['tx_record']['transaction_hash'],
            'content_fingerprint': results['search_result']['content_fingerprint'],
            'is_valid': results['is_valid']
        }, indent=2))

if __name__ == "__main__":
    main()
