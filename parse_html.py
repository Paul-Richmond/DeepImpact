import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

from scrapegraphai.graphs import SmartScraperGraph
from utils.io import WebArchiveDB, parse_arguments


# Load environment variables once at module level
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAIKEY")
if not OPENAI_API_KEY:
    raise EnvironmentError("OPENAIKEY environment variable not found. Please set it in your .env file.")


# Configure logging
def setup_logger() -> logging.Logger:
    """Set up and return configured logger."""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


logger = setup_logger()


def write_results_to_file(result: Dict[str, Any], filename: str) -> None:
    """
    Write content to a JSON file, creating directories if they don't exist.

    Args:
        result: The content to write (dictionary that will be serialized to JSON)
        filename: The target filename/path

    Raises:
        PermissionError: If write permissions are denied
        OSError: For other file operation errors
        TypeError: If result cannot be serialized to JSON
    """
    # Convert filename to Path object for easier handling
    file_path = Path(filename)

    # Create parent directories if they don't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Write the file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4, ensure_ascii=False)

        logger.info(f"Results have been written to {filename}")
    except TypeError as e:
        logger.error(f"JSON serialization error: {str(e)}")
        raise
    except PermissionError:
        logger.error(f"Permission denied when trying to write to {filename}")
        raise
    except OSError as e:
        logger.error(f"Error writing file: {str(e)}")
        raise


def load_html(file_path: str) -> str:
    """
    Load HTML content from a file.

    Args:
        file_path: Path to the HTML file

    Returns:
        String containing the HTML content

    Raises:
        FileNotFoundError: If the file doesn't exist
        OSError: For other file operation errors
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        logger.error(f"HTML file not found: {file_path}")
        raise
    except OSError as e:
        logger.error(f"Error reading HTML file: {str(e)}")
        raise


def get_graph_config() -> Dict[str, Any]:
    """
    Return the configuration for the SmartScraperGraph.

    Centralizes configuration to make it easier to modify.
    """
    return {
        "llm": {
            "api_key": OPENAI_API_KEY,
            "model": "openai/gpt-4o-mini",
            "temperature": 0.0,
        },
        "verbose": True,
    }


def get_scraping_prompt() -> str:
    """Return the prompt for the SmartScraperGraph."""
    return """You are an expert in Web Scraping, 
    so you are capable of extracting information from HTML and labelling it accordingly.
    Within the HTML are comments posted by readers of a news article. 
    From the HTML extract the following information for each posted comment:
    the readers' user name, the content of the comment and any information regarding the comment 
    such as the date and time it was posted, how many likes or dislikes the post has etc.
    """


def extract_comments_from_html(html_content: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract comment information from HTML using SmartScraperGraph.

    Args:
        html_content: HTML content to process
        config: Configuration for the SmartScraperGraph

    Returns:
        Extracted comment data
    """
    smart_scraper_graph = SmartScraperGraph(
        prompt=get_scraping_prompt(),
        source=html_content,
        config=config
    )

    return smart_scraper_graph.run()


if __name__ == "__main__":
    # Parse command line arguments
    args = parse_arguments()
    # Setup database connection
    db = WebArchiveDB(db_path='db/database.db', db_table_name=args.table)
    db_entries = db.execute_query(f'''SELECT * FROM {db.db_table_name}''')

    for entry in db_entries:
        idx = entry['id']
        input_html_path = entry['html_file']
        output_json_path = f'processed_comments/{db.db_table_name}/id_{idx}.json'

        # Load HTML
        html_content = load_html(input_html_path)
        logger.info(f"Successfully loaded HTML from {input_html_path}")

        # Extract comments
        config = get_graph_config()
        result = extract_comments_from_html(html_content, config)
        logger.info("Successfully extracted comments from HTML")

        # Write results
        write_results_to_file(result, output_json_path)
