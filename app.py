"""
Flask Web Application for Face Identification & Blockchain Verification Pipeline.
"""

import os
import sys
import tempfile
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

from face_engine import FaceEngine
from web_search import WebSearchEngine
from blockchain_verifier import BlockchainVerifier

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/verify')
def verify_page():
    return render_template('verify.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return render_template('index.html', logged_in=True, username="Alex Dev")
    return render_template('login.html')

@app.route('/api/run_pipeline', methods=['POST'])
def api_run_pipeline():
    try:
        # Extract identity metadata search fields
        search_name = request.form.get('search_name', '').strip()
        search_handle = request.form.get('search_handle', '').strip()
        photo_notes = request.form.get('photo_notes', '').strip()
        search_location = request.form.get('search_location', '').strip()
        search_occupation = request.form.get('search_occupation', '').strip()
        search_education = request.form.get('search_education', '').strip()
        search_website = request.form.get('search_website', '').strip()
        keywords = request.form.get('keywords', 'AI tech innovator keynote').strip()
        target_platforms = request.form.getlist('platforms')

        # Combine terms into an optimized search query string
        query_parts = [p for p in [search_name, search_handle, photo_notes, search_occupation, search_education, search_location, keywords] if p]
        full_query = " ".join(query_parts) if query_parts else (search_name or keywords)

        image_file = request.files.get('image')

        if image_file and image_file.filename != '':
            filename = secure_filename(image_file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(save_path)
        else:
            save_path = 'sample_face.jpg'

        if not os.path.exists(save_path):
            return jsonify({'success': False, 'error': f'Image file not found: {save_path}'}), 400

        # 1. Face Identification
        face_engine = FaceEngine()
        face_data = face_engine.process_image(save_path)

        # 2. Dynamic Web & Social Search with Identity Criteria
        search_engine = WebSearchEngine()
        search_result = search_engine.find_matching_post(
            face_data, 
            query_keywords=full_query,
            target_platforms=target_platforms
        )

        # 3. Blockchain Anchoring
        verifier = BlockchainVerifier(ledger_db_path="blockchain_ledger.json")
        tx_record = verifier.record_verification(face_data, search_result)

        # 4. Immediate Integrity Self-Verification
        is_valid, verify_details = verifier.verify_on_chain_record(
            tx_record["transaction_hash"],
            expected_content_fingerprint=search_result["content_fingerprint"]
        )

        return jsonify({
            'success': True,
            'face_data': face_data,
            'search_result': search_result,
            'tx_record': tx_record,
            'verification_result': verify_details
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/verify', methods=['GET'])
def api_verify():
    tx_hash = request.args.get('tx_hash', '').strip()
    if not tx_hash:
        return jsonify({'valid': False, 'error': 'Missing transaction hash (tx_hash)'}), 400

    verifier = BlockchainVerifier(ledger_db_path="blockchain_ledger.json")
    is_valid, details = verifier.verify_on_chain_record(tx_hash)

    return jsonify({
        'valid': is_valid,
        'details': details
    })

if __name__ == '__main__':
    print("\n=======================================================")
    print("  STARTING FACE ID & BLOCKCHAIN VERIFIER WEB SERVER")
    print("  Dashboard URL: http://127.0.0.1:5000")
    print("=======================================================\n")
    app.run(host='0.0.0.0', port=5000, debug=True)
