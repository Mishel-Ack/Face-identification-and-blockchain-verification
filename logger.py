import logging
import json
from pythonjsonlogger import jsonlogger
from datetime import datetime

def setup_logging(app=None):
    """Configure JSON logging for Flask app"""
    logger = logging.getLogger("veriface")
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        # JSON formatter
        logHandler = logging.StreamHandler()
        formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(message)s')
        logHandler.setFormatter(formatter)
        logger.addHandler(logHandler)

        # Also log to file
        file_handler = logging.FileHandler('app.log')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

class MetricsCollector:
    """Track performance metrics"""

    @staticmethod
    def log_api_request(route, method, status_code, response_time_ms):
        logger = logging.getLogger("veriface")
        logger.info({
            'event': 'api_request',
            'timestamp': datetime.utcnow().isoformat(),
            'route': route,
            'method': method,
            'status_code': status_code,
            'response_time_ms': response_time_ms
        })

    @staticmethod
    def log_pipeline_execution(face_count, search_time_ms, blockchain_time_ms):
        logger = logging.getLogger("veriface")
        logger.info({
            'event': 'pipeline_executed',
            'timestamp': datetime.utcnow().isoformat(),
            'face_count': face_count,
            'search_time_ms': search_time_ms,
            'blockchain_time_ms': blockchain_time_ms,
            'total_time_ms': search_time_ms + blockchain_time_ms
        })

    @staticmethod
    def log_error(error_type, error_message, stack_trace=None):
        logger = logging.getLogger("veriface")
        logger.error({
            'event': 'error',
            'timestamp': datetime.utcnow().isoformat(),
            'error_type': error_type,
            'error_message': error_message,
            'stack_trace': stack_trace
        })
