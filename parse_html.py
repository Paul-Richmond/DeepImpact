import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
from scrapegraphai.graphs import SmartScraperGraph
from typing import Optional

load_dotenv()
openaikey = os.getenv("OPENAIKEY")

# # Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def write_results_to_file(result: str, filename: str) -> Optional[str]:
    """
    Write content to a file, creating directories if they don't exist.

    Args:
        result (str): The content to write
        filename (str): The target filename/path

    Returns:
        Optional[str]: None if successful, error message if failed
    """
    try:
        # Convert filename to Path object for easier handling
        file_path = Path(filename)

        # Create parent directories if they don't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4)

        logger.info(f"Results have been written to {filename}")
        return None

    except PermissionError:
        logger.error(f"Permission denied when trying to write to {filename}")
        raise
    except OSError as e:
        logger.error(f"Error writing file: {str(e)}")
        raise


if __name__ == "__main__":
    html_path = 'scraped_html/database_dm_proxima_b/id_1.html'

    with open(html_path) as file:
        html = file.read()
    #
    # graph_config = {
    #    "llm": {
    #       "model": "ollama/deepseek-r1:1.5b",
    #       "temperature": 0,
    #       "format": "json",  # Ollama needs the format to be specified explicitly
    #       "model_tokens": 2000,  # depending on the model set context length
    #       "base_url": "http://localhost:11434",  # set ollama URL of the local host (YOU CAN CHANGE IT, if you have a different endpoint
    #    }
    # }

    graph_config = {"llm": {"api_key": openaikey,
                            "model": "openai/gpt-4o-mini",
                            "temperature": 0.0,
                            },
                    "verbose": True,
    }

    # ************************************************
    # Create the SmartScraperGraph instance and run it
    # ************************************************

    smart_scraper_graph = SmartScraperGraph(
       prompt='''You are an expert in Web Scraping, 
       so you are capable of extracting information from HTML and labelling it accordingly.
       Within the HTML are comments posted by readers of a news article. 
       From the HTML extract the following information for each posted comment:
       the readers' user name, the content of the comment and any information regarding the comment 
       such as the date and time it was posted, how many likes or dislikes the post has etc.
       ''',
       # also accepts a string with the already downloaded HTML code
       source=html,
       config=graph_config
    )

    llm_result = smart_scraper_graph.run()

    write_results_to_file(llm_result, f"processed_comments/database_dm_proxima_b/id_1.json")
