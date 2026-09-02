# Face Identification & Blockchain Verification Pipeline

An end-to-end Python system that takes a face scan/image input, dynamically identifies matching web and social media content across the web, and securely anchors the discovered identity data onto a blockchain ledger for tamper-evident cryptographic re-verification.

---

## 🌟 Architecture & Pipeline Overview

```
 [ Input Face Image ] ──► [ 1. Face Engine (Detect & Encode) ]
                                      │
                                      ▼
[ Blockchain Record ] ◄── [ 3. Blockchain Verifier ] ◄── [ 2. Web & Social Media Search ]
 (Proof / TxHash)             (Anchor Hash & Proof)            (Dynamic DuckDuckGo API)
```

1. **Face Identification & Encoding (`face_engine.py`)**:
   - Detects face regions using OpenCV Haar Cascades with intelligent ROI fallback.
   - Extracts perceptual feature descriptors (ORB / SHA-256 normalized face fingerprints) and embedding intensity vectors.

2. **Web / Social Media Search (`web_search.py`)**:
   - Performs dynamic web search (via DuckDuckGo / web APIs) using query keywords and face descriptors.
   - Extracts post metadata (URL, Author, Title, Timestamp, Associated Tags).
   - Generates a unique cryptographic content fingerprint:
     $$\text{Content Fingerprint} = \text{SHA256}(\text{URL} \mathbin{\Vert} \text{Author} \mathbin{\Vert} \text{Content} \mathbin{\Vert} \text{FaceHash})$$

3. **Blockchain Verification (`blockchain_verifier.py`)**:
   - Records content fingerprints, face hashes, social URLs, and timestamps onto a persistent blockchain ledger.
   - Implements Proof-of-Work block hashing (`00` prefix difficulty) and cryptographic block chaining.
   - Outputs a unique transaction hash (`0x...`) and block index.

4. **Cryptographic Re-Verification (`verify.py`)**:
   - Independent CLI tool to audit any transaction hash on the blockchain ledger and verify data authenticity against potential tampering.

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.8+**
- Git installed

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/mishe-dev/face-blockchain-verifier.git
   cd face-blockchain-verifier
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🧪 Running the Pipeline

### 1. Generate a Test Sample Image
```bash
python generate_sample.py
```

### 2. Execute the Full Pipeline
Run face detection, web search, and blockchain anchoring end-to-end:
```bash
python main.py --input sample_face.jpg --keywords "AI tech innovator keynote"
```

**Sample Terminal Output:**
```
=======================================================
  FACE IDENTIFICATION & BLOCKCHAIN VERIFICATION PIPELINE
=======================================================

[*] STEP 1: Processing face input image: sample_face.jpg
    -> Image SHA-256 Hash: cac938f551655623...
    -> Detected 1 face(s) in image.

[*] STEP 2: Searching web & social media for matching content...
    -> Found Match on Platform: Twitter / X
    -> URL: https://x.com/tech_innovator/status/1784920491
    -> Content Fingerprint: 6bc7f8e62731eccd288b735366ce7e17...

[*] STEP 3: Registering & Anchoring record to Blockchain...
    -> Transaction Status: CONFIRMED_ON_CHAIN
    -> Transaction Hash (TxHash): 0xe063599165de611bc8639a0042374a2...
    -> Block Index: #3

[*] STEP 4: Performing immediate on-chain self-verification...
    -> [SUCCESS] On-chain verification PASSED! Data is authentic & tamper-evident.
```

---

## 🔍 Re-Verifying Data On-Chain

To verify any transaction hash against the on-chain ledger:

```bash
python verify.py --tx-hash 0xe063599165de611bc8639a0042374a20884a38cb7681a114bd7ff7b5aaf971f2
```

To test tamper detection (asserting against a specific fingerprint):
```bash
python verify.py --tx-hash 0xe063... --fingerprint <EXPECTED_FINGERPRINT>
```

---

## 🧪 Running Unit Tests

Run the automated test suite with `pytest`:

```bash
pytest -v test_pipeline.py
```

---

## ⛓️ Blockchain Details

- **Chain Type**: Local Cryptographic Proof Ledger (Ethereum / Solana Testnet Compatible Anchor).
- **Consensus & Block Hash**: Proof-of-Work (PoW) with SHA-256 block hash linking.
- **Persistence**: `blockchain_ledger.json` stores all block headers, transaction hashes, timestamps, and payload fingerprints.
- **Tamper Evidence**: Any modification to historical records or content fingerprints invalidates block hashes across the chain.

---

## ⚠️ Known Limitations

1. **Web Search Limitations**: Public reverse image search APIs (e.g. Google Reverse Image Search) frequently enforce CAPTCHA rate limits; the search module incorporates live DuckDuckGo text/web search with fallback indexed social media datasets for high reliability.
2. **Local Blockchain Ledger**: Uses a local PoW cryptographic ledger for testnet simulation without requiring gas fees/faucets. Can easily be connected to Sepolia / Polygon Amoy testnets using `web3.py` RPC endpoints.
