import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

def setup_logging():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    log_dir = os.path.join(base_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    current_date = datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(log_dir, f'api_{current_date}.log')
    
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter(log_format)
    
    if not root_logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    return root_logger

logger = setup_logging()