import json
import hashlib
import time
import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, Tuple

from database import BlockchainDatabase
from encryption import FaceDataEncryptor

class BlockchainVerifier:
    def __init__(self, ledger_db_path: str = "blockchain.db", rpc_url: str = None):
        # Auto-correct ledger path if a legacy .json filename is passed
        if ledger_db_path.endswith(".json"):
            ledger_db_path = ledger_db_path.replace(".json", ".db")
        self.ledger_db_path = ledger_db_path
        self.rpc_url = rpc_url
        self.db = BlockchainDatabase(ledger_db_path)
        self.encryptor = FaceDataEncryptor()
        self._ensure_genesis()

    @property
    def blocks(self):
        """Backward compatibility helper property for legacy tests accessing verifier.blocks"""
        with sqlite3.connect(self.ledger_db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute('SELECT * FROM blocks ORDER BY id ASC').fetchall()
            result = []
            for r in rows:
                b_data = json.loads(r['block_data'])
                result.append(b_data)
            return result

    @blocks.setter
    def blocks(self, value):
        pass

    def _ensure_genesis(self):
        """Initializes Genesis Block if table is empty"""
        last_block = self.db.get_last_block()
        if not last_block:
            genesis_payload = {"message": "Genesis Block - Face ID & Social Data Ledger"}
            prev_hash = "0" * 64
            genesis_hash = self._calculate_hash(0, "2026-01-01T00:00:00Z", genesis_payload, prev_hash, 0)
            self.db.insert_block(
                transaction_hash="0x" + "0" * 64,
                face_hash="0" * 64,
                content_fingerprint="0" * 64,
                previous_hash=prev_hash,
                block_data={
                    "index": 0,
                    "timestamp": "2026-01-01T00:00:00Z",
                    "hash": genesis_hash,
                    "nonce": 0,
                    "data": genesis_payload,
                    "previous_hash": prev_hash,
                    "network": "Genesis Network"
                }
            )

    def _calculate_hash(self, index: int, timestamp: str, data: dict, previous_hash: str, nonce: int) -> str:
        payload = f"{index}{timestamp}{json.dumps(data, sort_keys=True)}{previous_hash}{nonce}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def record_verification(self, face_data: dict, search_result: dict) -> Dict[str, Any]:
        """
        Uploads & anchors discovered social post metadata and face hashes onto the SQLite blockchain ledger.
        Returns verifiable transaction record with transaction hash and block proof.
        """
        last_block = self.db.get_last_block()
        prev_hash = last_block["block_data"].get("hash", "0" * 64) if last_block else "0" * 64
        index = (last_block["block_data"].get("index", 0) + 1) if last_block else 1
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Encrypt embedding if present for privacy
        encrypted_embedding = None
        face_hash = "0x" + "0" * 64
        if face_data.get("faces") and len(face_data["faces"]) > 0:
            face_enc = face_data["faces"][0]["encoding"]
            face_hash = face_enc.get("face_hash", "0x" + "0" * 64)
            encrypted_embedding = self.encryptor.encrypt_embedding(face_enc)

        # Construct tamper-evident record payload
        post_meta = search_result.get("post_metadata", {})
        record_payload = {
            "record_type": "FACE_SOCIAL_IDENTIFICATION_PROOF",
            "face_image_hash": face_data.get("image_hash"),
            "face_count": face_data.get("face_count", 1),
            "social_post_url": post_meta.get("url", ""),
            "social_post_platform": post_meta.get("platform", ""),
            "social_post_author": post_meta.get("author", ""),
            "content_fingerprint": search_result.get("content_fingerprint", ""),
            "match_confidence": search_result.get("match_confidence", 1.0),
            "verification_index": index,
            "timestamp": search_result.get("discovered_at", timestamp),
            "encrypted_embedding": encrypted_embedding
        }

        # Simple Proof of Work simulation for block hashing
        nonce = 0
        block_hash = ""
        target_prefix = "00"
        
        while True:
            candidate_hash = self._calculate_hash(index, timestamp, record_payload, prev_hash, nonce)
            if candidate_hash.startswith(target_prefix):
                block_hash = candidate_hash
                break
            nonce += 1

        tx_payload = f"TX:{block_hash}:{record_payload['content_fingerprint']}:{timestamp}"
        tx_hash = "0x" + hashlib.sha256(tx_payload.encode()).hexdigest()
        active_network = os.getenv("BLOCKCHAIN_NETWORK", "Cryptographic SQLite Ledger (SHA-256 Proof Anchor)")

        block_data = {
            "index": index,
            "timestamp": timestamp,
            "transaction_hash": tx_hash,
            "data": record_payload,
            "previous_hash": prev_hash,
            "hash": block_hash,
            "nonce": nonce,
            "network": active_network
        }

        # Insert into SQLite Database
        self.db.insert_block(
            transaction_hash=tx_hash,
            face_hash=face_hash,
            content_fingerprint=record_payload['content_fingerprint'],
            previous_hash=prev_hash,
            block_data=block_data
        )

        return {
            "status": "CONFIRMED_ON_CHAIN",
            "transaction_hash": tx_hash,
            "block_index": index,
            "block_hash": block_hash,
            "previous_block_hash": prev_hash,
            "network": active_network,
            "timestamp": timestamp,
            "record_payload": record_payload
        }

    def verify_on_chain_record(self, tx_hash: str, expected_content_fingerprint: str = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Queries the blockchain ledger database to verify transaction hash integrity & tamper status.
        """
        block_row = self.db.get_block(tx_hash)
        if not block_row:
            return False, {"error": f"Transaction hash {tx_hash} not found in blockchain ledger."}

        if not block_row.get("is_valid", True):
            return False, {"error": "Block marked as invalid in ledger."}

        block_data = block_row["block_data"]
        data_payload = block_data.get("data", {})

        if expected_content_fingerprint and block_row.get("content_fingerprint") != expected_content_fingerprint:
            return False, {
                "error": "Fingerprint mismatch! Discovered content does not match on-chain record.",
                "on_chain_fingerprint": block_row.get("content_fingerprint"),
                "provided_fingerprint": expected_content_fingerprint
            }

        # Verify hash calculation
        calc_hash = self._calculate_hash(
            block_data["index"],
            block_data["timestamp"],
            data_payload,
            block_data["previous_hash"],
            block_data["nonce"]
        )
        if calc_hash != block_data["hash"]:
            return False, {"error": "Tampered block hash detected!"}

        return True, {
            "valid": True,
            "block_index": block_data["index"],
            "timestamp": block_data["timestamp"],
            "transaction_hash": tx_hash,
            "on_chain_data": data_payload,
            "verified_network": block_data.get("network")
        }

    def validate_full_chain(self) -> Tuple[bool, str]:
        """
        Validates full hash chain stored in SQLite database.
        """
        with sqlite3.connect(self.ledger_db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute('SELECT * FROM blocks ORDER BY id ASC').fetchall()

        if not rows:
            return False, "Chain is empty."

        for i, row in enumerate(rows):
            block_data = json.loads(row['block_data'])
            if block_data.get("index") != i:
                return False, f"Chain broken: Block index mismatch at position {i} (found {block_data.get('index')})."

            calc_hash = self._calculate_hash(
                block_data["index"],
                block_data["timestamp"],
                block_data.get("data", {}),
                block_data["previous_hash"],
                block_data["nonce"]
            )
            if calc_hash != block_data["hash"]:
                return False, f"Tampered block hash at block ID #{row['id']}"

            if i > 0:
                prev_block_data = json.loads(rows[i-1]['block_data'])
                if block_data["previous_hash"] != prev_block_data["hash"]:
                    return False, f"Broken link between block #{rows[i-1]['id']} and #{row['id']}"

        return True, "Chain integrity valid."
