import logging
import os

# Get the absolute path to the directory containing this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Set the log directory to be one level up from this file, in a "logs" folder
LOG_DIR = os.path.join(BASE_DIR, "..", "logs")

# Ensure the log directory exists (create if not present)
os.makedirs(LOG_DIR, exist_ok=True)

# Set the log file path
LOG_FILE = os.path.join(LOG_DIR, "dashboard.log")

# Create a logger with a specific name
logger = logging.getLogger("streamlit_dashboard")
logger.setLevel(logging.INFO)

# Only add handlers if there are none already (prevents duplicate logs if re-imported)
if not logger.hasHandlers():
    # FileHandler writes logs to a file (in utf-8 encoding)
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    # Formatter specifies the log message format (timestamp, level, message)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    # Attach the file handler to the logger
    logger.addHandler(file_handler)