"""
Canonical JSON Fingerprinting Module.
Creates deterministic SHA-256 hashes from structured verification records.
"""

import json
import hashlib
from typing import Dict, Any

def create_canonical_record(post_url: str, post_text: str, image_sha256: str, source: str, discovered_at: str) -> Dict[str, Any]:
    """
    Constructs a privacy-preserving canonical record without raw biometric data.
    """
    return {
        "discovered_at": discovered_at,
        "image_sha256": image_sha256,
        "post_text": post_text,
        "post_url": post_url,
        "source": source
    }

def compute_canonical_hash(record: Dict[str, Any]) -> str:
    """
    Computes deterministic SHA-256 fingerprint using sorted keys and compact separators.
    """
    canonical_bytes = json.dumps(record, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(canonical_bytes).hexdigest()

def compute_bytes32_hash(record: Dict[str, Any]) -> str:
    """
    Returns 0x-prefixed 32-byte hex string compatible with Solidity bytes32.
    """
    return "0x" + compute_canonical_hash(record)
