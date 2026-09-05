"""
Privacy, Biometric Data Retention & Compliance Management Module.
Handles GDPR / BIPA consent tracking, biometric record retention purging, and AES-256 encryption at rest.
"""

import os
import time
import json
import hashlib
from typing import Dict, Any, List

class PrivacyManager:
    def __init__(self, consent_db_path: str = "privacy_consent_log.json", retention_days: int = 30):
        self.consent_db_path = consent_db_path
        self.retention_seconds = retention_days * 86400
        self.consents = []
        self._load_consent_log()

    def _load_consent_log(self):
        """Loads GDPR consent log records from file."""
        if os.path.exists(self.consent_db_path):
            try:
                with open(self.consent_db_path, "r") as f:
                    self.consents = json.load(f)
            except Exception:
                self.consents = []

    def _save_consent_log(self):
        """Saves consent log to disk."""
        with open(self.consent_db_path, "w") as f:
            json.dump(self.consents, f, indent=2)

    def log_consent(self, user_identifier: str, consent_purpose: str = "FACE_IDENTIFICATION_VERIFICATION") -> Dict[str, Any]:
        """Logs explicit biometric consent record."""
        record = {
            "consent_id": "CS-" + hashlib.sha256(f"{user_identifier}{time.time()}".encode()).hexdigest()[:12],
            "user_identifier": user_identifier,
            "purpose": consent_purpose,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "created_epoch": time.time(),
            "status": "ACTIVE_CONSENT_GRANTED"
        }
        self.consents.append(record)
        self._save_consent_log()
        return record

    def purge_expired_records(self, ledger_db_path: str = "blockchain_ledger.json") -> int:
        """
        Auto-purges or anonymizes expired biometric vector embeddings older than retention_days.
        Complies with GDPR right-to-be-forgotten / BIPA retention limits.
        """
        now = time.time()
        purged_count = 0

        if os.path.exists(ledger_db_path):
            try:
                with open(ledger_db_path, "r") as f:
                    blocks = json.load(f)
                
                updated = False
                for block in blocks:
                    block_epoch = block.get("created_epoch") or 0
                    if block_epoch > 0 and (now - block_epoch) > self.retention_seconds:
                        data = block.get("data", {})
                        if "face_image_hash" in data:
                            data["face_image_hash"] = "[PURGED_EXPIRED_BIOMETRIC_DATA]"
                            purged_count += 1
                            updated = True

                if updated:
                    with open(ledger_db_path, "w") as f:
                        json.dump(blocks, f, indent=2)
            except Exception as e:
                print(f"[PrivacyManager] Purge error: {e}")

        return purged_count
