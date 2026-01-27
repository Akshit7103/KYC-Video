"""
Configuration settings for Video KYC AI Checker
"""

import os
from datetime import timedelta

class Config:
    """Base configuration"""

    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = True

    # File upload settings
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB max file size
    UPLOAD_FOLDER = 'data/videos'
    DOCUMENTS_FOLDER = 'data/documents'
    ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}
    ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'pdf'}

    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)

    # AI Model settings (for future implementation)
    LIVENESS_THRESHOLD = 70  # Minimum score for liveness detection (0-100)
    FACE_MATCH_THRESHOLD = 75  # Minimum score for face matching (0-100)
    SCRIPT_COMPLIANCE_THRESHOLD = 80  # Minimum score for script compliance (0-100)
    BEHAVIOR_THRESHOLD = 50  # Minimum score for behavior (below = suspicious)

    # Decision Engine weights
    WEIGHTS = {
        'liveness': 0.25,
        'face_recognition': 0.25,
        'script_compliance': 0.20,
        'document_verification': 0.15,
        'behavior_analysis': 0.10,
        'consent_verification': 0.05
    }

    # RBI Compliance settings
    CONSENT_REQUIRED = True
    AADHAAR_REDACTION_REQUIRED = True
    MANDATORY_QUESTIONS_COUNT = 15  # Minimum mandatory questions

    # Video processing settings
    FRAME_EXTRACTION_RATE = 1  # Extract 1 frame per second
    AUDIO_SAMPLE_RATE = 16000  # Audio sampling rate for speech-to-text

    # Report settings
    REPORT_FORMAT = 'json'  # 'json' or 'pdf'
    REPORTS_FOLDER = 'outputs/reports'

    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'logs/app.log'


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    # Override with strong secret key
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'CHANGE-THIS-IN-PRODUCTION'


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    # Use temporary folders for testing
    UPLOAD_FOLDER = 'tests/temp_videos'
    DOCUMENTS_FOLDER = 'tests/temp_documents'


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(config_name='default'):
    """Get configuration by name"""
    return config.get(config_name, config['default'])
