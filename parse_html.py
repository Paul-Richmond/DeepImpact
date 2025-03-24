import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from scrapegraphai.graphs import SmartScraperGraph

from scrapers.database import WebArchiveDB
from scrapers.utils import parse_arguments

# Load environment variables once at module level
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAIKEY")
if not OPENAI_API_KEY:
    raise EnvironmentError("OPENAIKEY environment variable not found. Please set it in your .env file.")

logger = logging.getLogger(__name__)


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
    # Could use
    # return {
    #     "llm": {
    #         "model": "ollama/deepseek-r1:1.5b",
    #         "temperature": 0,
    #         "format": "json",  # Ollama needs the format to be specified explicitly
    #         "model_tokens": 2000,  # depending on the model set context length
    #         "base_url": "http://localhost:11434",
    #         # set ollama URL of the local host (YOU CAN CHANGE IT, if you have a different endpoint)
    #     },
    #     "verbose": True,
    # }
    return {
        "llm": {
            "api_key": OPENAI_API_KEY,
            "model": "openai/gpt-4o-mini",
            "temperature": 0.0,
        },
        "verbose": True,
    }


def get_scraping_prompt(site_type: str) -> str:
    """
    Return the prompt for the SmartScraperGraph based on the site type.

    Args:
        site_type: The type of website (e.g., 'The Guardian', 'BBC', 'Daily Mail')

    Returns:
        String containing the prompt for the specific site
    """
    # Base prompt common to all sites
    base_prompt =  """You are an expert in Web Scraping capable of extracting information from HTML and labelling it accordingly.
    Within the HTML are comments posted by readers of a news article. 
    From the HTML extract the following information for each posted comment:
    the readers' user name, the content of the comment and any information regarding the comment 
    such as the date and time it was posted, how many likes or dislikes the post has etc.
    """

    # Site-specific prompts
    prompts = {
        "The Guardian": f"""{base_prompt}""",

        "Daily Mail": f"""{base_prompt}""",

        "BBC": f"""{base_prompt}""",
    }

    # Return site-specific prompt if available, otherwise return default prompt
    return prompts.get(site_type, base_prompt)


def extract_comments_from_html(html_content: str, config: Dict[str, Any], site_type: str) -> Dict[str, Any]:
    """
    Extract comment information from HTML using SmartScraperGraph.

    Args:
        html_content: HTML content to process
        config: Configuration for the SmartScraperGraph
        site_type: Type of website for customized prompting

    Returns:
        Extracted comment data
    """
    prompt = get_scraping_prompt(site_type)

    smart_scraper_graph = SmartScraperGraph(
        prompt=prompt,
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
        site = entry['site']
        input_html_path = entry['html_file']
        output_json_path = f'processed_comments/{db.db_table_name}/id_{idx}.json'

        # Load HTML
        html_content = load_html(input_html_path)
        logger.info(f"Successfully loaded HTML from {input_html_path}")

        # Extract comments
        config = get_graph_config()
        result = extract_comments_from_html(html_content, config, site)
        logger.info("Successfully extracted comments from HTML")

        # Add the llm configuration used
        config["llm"].pop("api_key", None)
        result.update({"llm": config["llm"]})

        # Write results
        write_results_to_file(result, output_json_path)
