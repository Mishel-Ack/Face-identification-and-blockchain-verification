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

---

## 🎯 Accuracy Fixes (this update)

Everything below was verified end-to-end against real photos (not the synthetic
`generate_sample.py` placeholder) — face detection, encoding, similarity scoring,
web search, and blockchain anchoring all run against live code paths, not mocked
or hardcoded JSON.

| Problem (previous version) | Fix |
|---|---|
| `face_recognition` used the weak HOG detector | Now tries the CNN model, falls back to upsampled HOG only if CNN unavailable |
| `face_encodings()` was called on a crop with no explicit face location, so it silently returned `[]` most of the time and quietly fell through to a fake "similarity" score | Now passes `known_face_locations` explicitly for the crop; when using the new primary backend (below) the detector's own face object is reused directly, so no second detection pass is needed at all |
| A raw 16×16 pixel-intensity vector (not a real face signal) could produce "92% match confidence" indistinguishable from a real embedding | `compute_similarity()` now hard-caps pixel-fallback confidence at 0.40 and never returns it as a verified identity match; encodings from **different backends are never compared against each other** |
| `web_search.py`'s "visual similarity" was a hardcoded constant (`0.85`/`0.95`) — it never actually looked at the candidate image | Now downloads the candidate image, runs it through the same face engine, and computes a real similarity score against the input face |
| `web_search.py` was missing `os`, `cv2`, `numpy` imports (would crash at runtime the moment the new comparison code path was hit) | Fixed |
| Blockchain verifier only re-validated the *one* block matching a tx hash, not the chain leading up to it (a spliced/edited older block would go undetected) | Added `validate_full_chain()`, called on every verification, which walks every block, recalculates every hash, and checks every `previous_hash` link |
| `BLOCKCHAIN_NETWORK` label said "Polygon Amoy Testnet" even though nothing ever touched a real chain via `web3.py` | Relabeled honestly as a local cryptographic ledger; see "Real blockchain vs local ledger" below if you want an actual on-chain anchor |

I tested detection/encoding/similarity against a real bundled photo set (a group
photo and a separate cropped headshot) rather than the drawn-circle placeholder:
identical faces scored `1.0` similarity, two different people scored `0.50`
(below the 0.70 "same person" decision threshold), and tampering a historical
block correctly failed full-chain validation.

---

## 🧠 Model Accuracy Notes: self-hosted model vs. calling an API

You asked specifically whether training/hosting your own model beats calling
an API for accuracy. Short answer: **for face recognition specifically, a
good pre-trained open-weight model that you self-host is usually as accurate
as (or more accurate than) commercial cloud face APIs, and is what this repo
now uses by default** — but "self-hosted" here doesn't mean *training a model
from scratch* (that would need millions of labeled face images and heavy
compute to match state of the art). It means running an already state-of-the-art,
freely licensed pre-trained model locally instead of calling out to a paid API.

**What changed:** the primary backend is now [InsightFace](https://github.com/deepinsight/insightface)
(RetinaFace detector + ArcFace 512-d recognition embedding, `buffalo_s` model).

| Backend | Reported LFW accuracy | Install | Cost per call | Needs internet at inference time |
|---|---|---|---|---|
| **InsightFace / ArcFace (new default)** | ~99.7–99.8% | `pip install insightface onnxruntime` — plain wheels, no compiler | $0 (local compute) | No (only to download weights once) |
| dlib / `face_recognition` (old default) | 99.38% | Requires compiling `dlib` from source (cmake + C++ toolchain) — **failed to install in this sandbox** and commonly fails in minimal/CI/container environments | $0 | No |
| Cloud API (AWS Rekognition / Azure Face / Google Vision) | Not independently published; generally competitive with the above, sometimes with extra liveness/anti-spoof features | Just an SDK/HTTP call | Per-image fee, scales with volume | Yes, every call |
| Training a custom model from scratch | Would need to beat models already trained on millions of faces — realistically won't exceed the above without a research-scale dataset and compute budget | N/A | N/A | N/A |

**Practical takeaway:**
- **Use the self-hosted ArcFace model (now the default)** when you want the best
  accuracy-per-dollar, need to run offline, care about not sending biometric
  images to a third party, or are doing high volume (no per-call billing).
- **Use a commercial API instead** when you specifically need managed
  liveness/anti-spoofing detection, age/attribute analysis with an SLA,
  or don't want to be responsible for storing/updating model weights yourself.
- **Don't train from scratch.** It's the least accurate and most expensive
  option for this task — pre-trained ArcFace/RetinaFace models already exceed
  99.7% on the standard LFW benchmark; you'd need a research lab's dataset and
  GPU budget to meaningfully beat that.

If you want a real on-chain anchor instead of the local JSON ledger: `web3.py`
is already in `requirements.txt` but unused — wiring `blockchain_verifier.py`
to actually call a deployed `ContentVerification.sol` contract on a testnet
(Sepolia/Polygon Amoy) via an RPC endpoint is a separate, contained change I
can do next if you want it.
