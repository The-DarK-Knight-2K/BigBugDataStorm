import logging
import os
import sys

def setup_logger(name="pipeline"):
    """
    Sets up a centralized logger that outputs to both the console and a file.
    """
    logger = logging.getLogger(name)
    
    # Avoid adding handlers multiple times if the logger is already set up
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Format: 2026-05-16 14:00:00,000 | INFO     | module | Message
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(module)s | %(message)s'
        )
        
        # Ensure outputs directory exists
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        outputs_dir = os.path.join(base_dir, 'outputs')
        os.makedirs(outputs_dir, exist_ok=True)
        
        # File Handler
        log_file = os.path.join(outputs_dir, 'pipeline.log')
        file_handler = logging.FileHandler(log_file, mode='a')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        
        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
    return logger
