import sqlite3
import os
import json

class BlockchainDatabase:
    def __init__(self, db_path='blockchain.db'):
        self.is_memory = (db_path == ':memory:')
        if not self.is_memory:
            if os.path.exists(db_path) and not db_path.endswith('.db') and not db_path.endswith('.sqlite'):
                db_path = db_path + '.db'
        self.db_path = db_path
        
        # If in-memory, retain persistent connection for instance lifetime
        self._shared_conn = sqlite3.connect(':memory:') if self.is_memory else None
        self._init_db()

    def _get_connection(self):
        if self.is_memory:
            return self._shared_conn
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Create tables if they don't exist"""
        conn = self._get_connection()
        conn.execute('''
            CREATE TABLE IF NOT EXISTS blocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_hash TEXT UNIQUE NOT NULL,
                face_hash TEXT NOT NULL,
                content_fingerprint TEXT,
                previous_hash TEXT,
                block_data TEXT,  -- JSON
                is_valid BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_transaction_hash ON blocks(transaction_hash)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_face_hash ON blocks(face_hash)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON blocks(created_at)')
        conn.commit()
        if not self.is_memory:
            conn.close()

    def insert_block(self, transaction_hash, face_hash, content_fingerprint, previous_hash, block_data):
        """Insert a new block"""
        conn = self._get_connection()
        conn.execute('''
            INSERT INTO blocks 
            (transaction_hash, face_hash, content_fingerprint, previous_hash, block_data, is_valid)
            VALUES (?, ?, ?, ?, ?, 1)
        ''', (
            transaction_hash,
            face_hash,
            content_fingerprint,
            previous_hash,
            json.dumps(block_data)
        ))
        conn.commit()
        if not self.is_memory:
            conn.close()

    def get_block(self, transaction_hash):
        """Retrieve a block by transaction hash"""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            'SELECT * FROM blocks WHERE transaction_hash = ?',
            (transaction_hash,)
        )
        row = cursor.fetchone()
        res = None
        if row:
            res = {
                'id': row['id'],
                'transaction_hash': row['transaction_hash'],
                'face_hash': row['face_hash'],
                'content_fingerprint': row['content_fingerprint'],
                'previous_hash': row['previous_hash'],
                'block_data': json.loads(row['block_data']),
                'is_valid': bool(row['is_valid']),
                'created_at': row['created_at']
            }
        if not self.is_memory:
            conn.close()
        return res

    def get_last_block(self):
        """Retrieve the most recent block"""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.execute('SELECT * FROM blocks ORDER BY id DESC LIMIT 1')
        row = cursor.fetchone()
        res = None
        if row:
            res = {
                'id': row['id'],
                'transaction_hash': row['transaction_hash'],
                'face_hash': row['face_hash'],
                'content_fingerprint': row['content_fingerprint'],
                'previous_hash': row['previous_hash'],
                'block_data': json.loads(row['block_data']),
                'is_valid': bool(row['is_valid']),
                'created_at': row['created_at']
            }
        if not self.is_memory:
            conn.close()
        return res

    def verify_block(self, transaction_hash, expected_fingerprint=None):
        """Verify a block's integrity"""
        block = self.get_block(transaction_hash)
        if not block:
            return False, "Block not found"

        if expected_fingerprint and block['content_fingerprint'] != expected_fingerprint:
            return False, "Content fingerprint mismatch"

        if not block['is_valid']:
            return False, "Block marked as invalid"

        return True, "Block verified"
