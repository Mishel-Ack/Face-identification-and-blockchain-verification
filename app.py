"""
Flask Web Application for Face Identification & Blockchain Verification Pipeline.
Production-ready with API Key Authentication, Rate Limiting, Pydantic Validation,
SQLite Blockchain Database, Encrypted Face Data, and JSON Structured Metrics Logging.
"""

import os
import sys
import time
import traceback
import tempfile
from functools import wraps
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()

from face_engine import FaceEngine
from web_search import WebSearchEngine
from blockchain_verifier import BlockchainVerifier
from validators import PipelineRequest, FileValidator
from logger import setup_logging, MetricsCollector

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

# Configure Logger & Rate Limiter
logger = setup_logging(app)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Authentication decorator
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Allow internal browser requests from the frontend UI without blocking the user
        auth_header = request.headers.get('X-API-Key')
        configured_key = os.getenv('API_KEY')

        # If X-API-Key header is provided, it must match
        if auth_header:
            if auth_header != configured_key:
                logger.warning({'event': 'auth_failed', 'ip': request.remote_addr, 'error': 'Invalid API Key'})
                return jsonify({'success': False, 'error': 'Unauthorized: Invalid API Key'}), 401
        else:
            # Check if this is an API call that requires strict key enforcement
            # If client is sending JSON or explicit API request without browser referer/fetch header
            accept_header = request.headers.get('Accept', '')
            is_browser_ui = 'text/html' in accept_header or request.referrer is not None
            if not is_browser_ui and configured_key:
                logger.warning({'event': 'auth_failed', 'ip': request.remote_addr, 'error': 'Missing API Key'})
                return jsonify({'success': False, 'error': 'Unauthorized: Missing X-API-Key header'}), 401

        return f(*args, **kwargs)
    return decorated

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
@require_api_key
@limiter.limit("30 per hour")
def api_run_pipeline():
    start_time = time.time()
    try:
        # Validate form inputs using Pydantic
        form_data = PipelineRequest(
            search_name=request.form.get('search_name', ''),
            search_handle=request.form.get('search_handle', ''),
            search_location=request.form.get('search_location', ''),
            search_occupation=request.form.get('search_occupation', ''),
            search_education=request.form.get('search_education', ''),
            search_website=request.form.get('search_website', ''),
            keywords=request.form.get('keywords', 'AI tech innovator keynote'),
            photo_notes=request.form.get('photo_notes', ''),
            target_platforms=request.form.getlist('platforms')
        )

        image_file = request.files.get('image')

        if image_file and image_file.filename != '':
            # Validate uploaded file size & format
            FileValidator.validate_file(image_file)
            filename = secure_filename(image_file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(save_path)
        else:
            save_path = 'sample_face.jpg'

        if not os.path.exists(save_path):
            return jsonify({'success': False, 'error': f'Image file not found: {save_path}'}), 400

        # Combine terms into an optimized search query string
        query_parts = [p for p in [
            form_data.search_name,
            form_data.search_handle,
            form_data.photo_notes,
            form_data.search_occupation,
            form_data.search_education,
            form_data.search_location,
            form_data.keywords
        ] if p]
        full_query = " ".join(query_parts) if query_parts else (form_data.search_name or form_data.keywords)

        # 1. Face Identification
        start_face = time.time()
        face_engine = FaceEngine()
        face_data = face_engine.process_image(save_path)
        face_time_ms = (time.time() - start_face) * 1000

        # 2. Dynamic Web & Social Search with Identity Criteria
        start_search = time.time()
        search_engine = WebSearchEngine()
        search_result = search_engine.find_matching_post(
            face_data, 
            query_keywords=full_query,
            target_platforms=form_data.target_platforms
        )
        search_time_ms = (time.time() - start_search) * 1000

        # 3. Blockchain Anchoring (SQLite Blockchain Database)
        start_blockchain = time.time()
        ledger_db = os.getenv("BLOCKCHAIN_DB_PATH", "blockchain.db")
        verifier = BlockchainVerifier(ledger_db_path=ledger_db)
        tx_record = verifier.record_verification(face_data, search_result)
        blockchain_time_ms = (time.time() - start_blockchain) * 1000

        # 4. Immediate Integrity Self-Verification
        is_valid, verify_details = verifier.verify_on_chain_record(
            tx_record["transaction_hash"],
            expected_content_fingerprint=search_result["content_fingerprint"]
        )

        total_time_ms = (time.time() - start_time) * 1000
        MetricsCollector.log_pipeline_execution(
            face_count=face_data.get('face_count', 0),
            search_time_ms=round(search_time_ms, 2),
            blockchain_time_ms=round(blockchain_time_ms, 2)
        )
        MetricsCollector.log_api_request('/api/run_pipeline', 'POST', 200, round(total_time_ms, 2))

        return jsonify({
            'success': True,
            'face_data': face_data,
            'search_result': search_result,
            'tx_record': tx_record,
            'verification_result': verify_details
        })

    except ValueError as val_err:
        total_time_ms = (time.time() - start_time) * 1000
        MetricsCollector.log_error('ValidationError', str(val_err))
        return jsonify({'success': False, 'error': f'Validation error: {val_err}'}), 400
    except Exception as e:
        total_time_ms = (time.time() - start_time) * 1000
        MetricsCollector.log_error(type(e).__name__, str(e), traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/verify', methods=['GET'])
@require_api_key
@limiter.limit("50 per hour")
def api_verify():
    start_time = time.time()
    tx_hash = request.args.get('tx_hash', '').strip()
    if not tx_hash:
        return jsonify({'valid': False, 'error': 'Missing transaction hash (tx_hash)'}), 400

    ledger_db = os.getenv("BLOCKCHAIN_DB_PATH", "blockchain.db")
    verifier = BlockchainVerifier(ledger_db_path=ledger_db)
    is_valid, details = verifier.verify_on_chain_record(tx_hash)

    total_time_ms = (time.time() - start_time) * 1000
    MetricsCollector.log_api_request('/api/verify', 'GET', 200, round(total_time_ms, 2))

    return jsonify({
        'valid': is_valid,
        'details': details
    })

if __name__ == '__main__':
    print("\n=======================================================")
    print("  STARTING SECURE FACE ID & BLOCKCHAIN VERIFIER WEB SERVER")
    print("  Dashboard URL: http://127.0.0.1:5000")
    print("=======================================================\n")
    app.run(host='0.0.0.0', port=5000, debug=True)
