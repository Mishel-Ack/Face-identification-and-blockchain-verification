"""
Blockchain Verification & Cryptographic Ledger Module.
Handles uploading content fingerprints, post metadata, and visual hashes
to an immutable on-chain record and provides cryptographic re-verification.
"""

import json
import hashlib
import time
import os
from typing import Dict, Any, Tuple

class BlockchainVerifier:
    def __init__(self, ledger_db_path: str = "blockchain_ledger.json", rpc_url: str = None):
        self.ledger_db_path = ledger_db_path
        self.rpc_url = rpc_url
        self.blocks = []
        self._load_ledger()

    def _load_ledger(self):
        """Loads existing blocks from persistent JSON storage or initializes Genesis Block."""
        if os.path.exists(self.ledger_db_path):
            try:
                with open(self.ledger_db_path, "r") as f:
                    self.blocks = json.load(f)
                return
            except Exception:
                pass

        # Create Genesis Block if ledger is empty
        genesis_data = {"message": "Genesis Block - Face ID & Social Data Ledger"}
        genesis_block = {
            "index": 0,
            "timestamp": "2026-01-01T00:00:00Z",
            "data": genesis_data,
            "previous_hash": "0" * 64,
            "hash": self._calculate_block_hash(0, "2026-01-01T00:00:00Z", genesis_data, "0" * 64, 0),
            "nonce": 0
        }
        self.blocks = [genesis_block]
        self._save_ledger()

    def _save_ledger(self):
        """Saves blocks to persistent file."""
        with open(self.ledger_db_path, "w") as f:
            json.dump(self.blocks, f, indent=2)

    def _calculate_block_hash(self, index: int, timestamp: str, data: dict, previous_hash: str, nonce: int) -> str:
        payload = f"{index}{timestamp}{json.dumps(data, sort_keys=True)}{previous_hash}{nonce}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def record_verification(self, face_data: dict, search_result: dict) -> Dict[str, Any]:
        """
        Uploads & anchors discovered social post metadata and face hashes onto the blockchain.
        Returns verifiable transaction record with transaction hash and block proof.
        """
        prev_block = self.blocks[-1]
        index = len(self.blocks)
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Construct tamper-evident record payload (Inspired by MachineLearningNft state tracking)
        record_payload = {
            "record_type": "FACE_SOCIAL_IDENTIFICATION_PROOF",
            "face_image_hash": face_data.get("image_hash"),
            "face_count": face_data.get("face_count", 1),
            "social_post_url": search_result["post_metadata"]["url"],
            "social_post_platform": search_result["post_metadata"]["platform"],
            "social_post_author": search_result["post_metadata"]["author"],
            "content_fingerprint": search_result["content_fingerprint"],
            "match_confidence": search_result.get("match_confidence", 1.0),
            "verification_count": len(self.blocks),  # Incremental verification count
            "timestamp": search_result.get("discovered_at", timestamp)
        }

        # Simple Proof of Work simulation for block hashing
        nonce = 0
        block_hash = ""
        target_prefix = "00"  # Lightweight PoW difficulty target
        
        while True:
            candidate_hash = self._calculate_block_hash(index, timestamp, record_payload, prev_block["hash"], nonce)
            if candidate_hash.startswith(target_prefix):
                block_hash = candidate_hash
                break
            nonce += 1

        tx_payload = f"TX:{block_hash}:{record_payload['content_fingerprint']}:{timestamp}"
        tx_hash = "0x" + hashlib.sha256(tx_payload.encode()).hexdigest()

        active_network = os.getenv("BLOCKCHAIN_NETWORK", "Cryptographic Local Ledger (SHA-256 Proof Anchor)")

        new_block = {
            "index": index,
            "timestamp": timestamp,
            "transaction_hash": tx_hash,
            "data": record_payload,
            "previous_hash": prev_block["hash"],
            "hash": block_hash,
            "nonce": nonce,
            "network": active_network
        }

        self.blocks.append(new_block)
        self._save_ledger()

        return {
            "status": "CONFIRMED_ON_CHAIN",
            "transaction_hash": tx_hash,
            "block_index": index,
            "block_hash": block_hash,
            "previous_block_hash": prev_block["hash"],
            "network": new_block["network"],
            "timestamp": timestamp,
            "record_payload": record_payload
        }

    def validate_full_chain(self) -> Tuple[bool, str]:
        """
        Rigorously validates the entire hash chain from Genesis block down to the tip.
        Checks block indices, previous hash linkage, and hash recalculations.
        """
        if not self.blocks:
            return False, "Chain is empty."

        for i, block in enumerate(self.blocks):
            if block.get("index") != i:
                return False, f"Chain broken: Block index mismatch at step {i} (found {block.get('index')})."

            calc_hash = self._calculate_block_hash(
                block["index"],
                block["timestamp"],
                block["data"],
                block["previous_hash"],
                block["nonce"]
            )
            if calc_hash != block["hash"]:
                return False, f"Tampered block hash at index #{i}!"

            if i > 0:
                prev_block = self.blocks[i - 1]
                if block["previous_hash"] != prev_block["hash"]:
                    return False, f"Broken link between block #{i-1} and #{i}! Previous hash mismatch."

        return True, "Chain integrity valid."

    def send_web3_smart_contract_tx(self, content_fingerprint: str) -> Dict[str, Any]:
        """
        Submits real bytes32 content fingerprint transaction to ContentVerification.sol smart contract via Web3 RPC.
        Enabled when environment variables `WEB3_RPC_URL`, `WEB3_PRIVATE_KEY`, and `WEB3_CONTRACT_ADDRESS` are configured.
        """
        rpc_url = self.rpc_url or os.getenv("WEB3_RPC_URL")
        private_key = os.getenv("WEB3_PRIVATE_KEY")
        contract_address = os.getenv("WEB3_CONTRACT_ADDRESS")

        if not rpc_url or not private_key or not contract_address:
            return {"web3_enabled": False, "reason": "Missing WEB3_RPC_URL, WEB3_PRIVATE_KEY, or WEB3_CONTRACT_ADDRESS"}

        try:
            from web3 import Web3
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            if not w3.is_connected():
                return {"web3_enabled": False, "reason": f"Could not connect to Web3 RPC at {rpc_url}"}

            account = w3.eth.account.from_key(private_key)
            contract_abi = [
                {
                    "inputs": [{"name": "contentHash", "type": "bytes32"}],
                    "name": "registerRecord",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                {
                    "inputs": [{"name": "contentHash", "type": "bytes32"}],
                    "name": "verifyRecord",
                    "outputs": [
                        {"name": "exists", "type": "bool"},
                        {"name": "timestamp", "type": "uint256"},
                        {"name": "uploader", "type": "address"}
                    ],
                    "stateMutability": "view",
                    "type": "function"
                }
            ]

            contract = w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=contract_abi)
            
            # Format bytes32
            if not content_fingerprint.startswith("0x"):
                bytes32_hash = "0x" + content_fingerprint
            else:
                bytes32_hash = content_fingerprint

            # Build & send transaction
            nonce = w3.eth.get_transaction_count(account.address)
            tx = contract.functions.registerRecord(bytes32_hash).build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gas': 150000,
                'gasPrice': w3.eth.gas_price
            })

            signed_tx = w3.eth.account.sign_transaction(tx, private_key=private_key)
            tx_hash_bytes = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            onchain_tx_hash = w3.to_hex(tx_hash_bytes)

            return {
                "web3_enabled": True,
                "status": "SUBMITTED_TO_TESTNET",
                "onchain_tx_hash": onchain_tx_hash,
                "contract_address": contract_address,
                "uploader": account.address,
                "network_id": w3.eth.chain_id
            }
        except Exception as e:
            print(f"[BlockchainVerifier] Web3 contract error: {e}")
            return {"web3_enabled": False, "reason": str(e)}

    def verify_on_chain_record(self, tx_hash: str, expected_content_fingerprint: str = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Queries the blockchain ledger to verify transaction hash integrity & tamper status.
        Performs a full chain walk to ensure overall chain continuity and block validity.
        """
        chain_ok, chain_msg = self.validate_full_chain()
        if not chain_ok:
            return False, {"error": f"Blockchain validation failed: {chain_msg}"}

        for block in self.blocks:
            if block.get("transaction_hash") == tx_hash:
                data = block["data"]
                if expected_content_fingerprint and data.get("content_fingerprint") != expected_content_fingerprint:
                    return False, {
                        "error": "Fingerprint mismatch! Discovered content does not match on-chain record.",
                        "on_chain_fingerprint": data.get("content_fingerprint"),
                        "provided_fingerprint": expected_content_fingerprint
                    }

                return True, {
                    "valid": True,
                    "block_index": block["index"],
                    "timestamp": block["timestamp"],
                    "transaction_hash": tx_hash,
                    "on_chain_data": data,
                    "verified_network": block.get("network")
                }

        return False, {"error": f"Transaction hash {tx_hash} not found in blockchain ledger."}
