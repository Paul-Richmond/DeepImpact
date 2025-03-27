"""
Logging setup module.

This module provides functionality to configure logging for applications, including
logging to the console and optionally to a file. It supports customization of log
levels and formats.

Functions:
    - setup_logging: Configures the root logger with specified settings.
"""

import logging
import sys


def setup_logging(log_level=logging.INFO, log_file=None) -> logging.Logger:
    """
    Configures the root logger with the specified log level and optional log file.

    The function sets up a default logging configuration that includes:
    - Console logging, which outputs log messages to stdout.
    - Optional file logging, if a log file path is provided.

    Args:
        log_level (int): The logging level (e.g., logging.INFO, logging.DEBUG).
        log_file (str, optional): Path to a file where logs will be written. If None, logging to a file is disabled.

    Returns:
        logging.Logger: The configured root logger instance.
    """
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    return root_logger
