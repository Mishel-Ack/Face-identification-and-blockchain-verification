"""
Verification CLI Tool to inspect and verify on-chain records against local image/metadata files.

Usage:
  python verify.py --tx-hash <0xTX_HASH> [--fingerprint <CONTENT_FINGERPRINT>]
"""

import argparse
import sys
from blockchain_verifier import BlockchainVerifier

def verify_tx(tx_hash: str, fingerprint: str = None):
    print("\n=======================================================")
    print("      BLOCKCHAIN ON-CHAIN RECORD AUDITOR & VERIFIER")
    print("=======================================================\n")
    
    print(f"[*] Querying Blockchain Ledger for Transaction Hash:")
    print(f"    {tx_hash}\n")

    verifier = BlockchainVerifier(ledger_db_path="blockchain_ledger.json")
    is_valid, details = verifier.verify_on_chain_record(tx_hash, expected_content_fingerprint=fingerprint)

    if is_valid:
        print("[+] VERIFICATION SUCCESSFUL: On-Chain Proof Validated!")
        print(f"    -> Block Index: #{details['block_index']}")
        print(f"    -> Timestamp: {details['timestamp']}")
        print(f"    -> Network: {details['verified_network']}")
        print("\n[+] On-Chain Payload Metadata:")
        on_chain_data = details["on_chain_data"]
        print(f"    - Social URL: {on_chain_data.get('social_post_url')}")
        print(f"    - Author: {on_chain_data.get('social_post_author')}")
        print(f"    - Platform: {on_chain_data.get('social_post_platform')}")
        print(f"    - Content Fingerprint: {on_chain_data.get('content_fingerprint')}")
        print(f"    - Face Image Hash: {on_chain_data.get('face_image_hash')}")
        print(f"    - Match Confidence: {on_chain_data.get('match_confidence', 0) * 100}%")
    else:
        print("[-] VERIFICATION FAILED!")
        print(f"    Error Reason: {details.get('error')}")
        if "on_chain_fingerprint" in details:
            print(f"    On-Chain Fingerprint:  {details['on_chain_fingerprint']}")
            print(f"    Provided Fingerprint:  {details['provided_fingerprint']}")

    print("\n=======================================================\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify on-chain face identification records")
    parser.add_argument("--tx-hash", "-t", type=str, required=True, help="Transaction hash to verify on-chain")
    parser.add_argument("--fingerprint", "-f", type=str, default=None, help="Optional content fingerprint to assert against on-chain record")

    args = parser.parse_args()
    verify_tx(args.tx_hash, args.fingerprint)
