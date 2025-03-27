# DeepImpact

A tool for analyzing the societal impact of scientific discoveries through web scraping and natural language processing.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Usage](#usage)
    - [Database Setup](#database-setup)
    - [Step 1: Scraping News Articles](#step-1-scraping-news-articles)
    - [Step 2: Processing Comments](#step-2-processing-comments)
- [Configuration](#configuration)
    - [Site-Specific Configurations](#site-specific-configurations)
- [Supported News Sites](#supported-news-sites)
- [How It Works](#how-it-works)
- [References](#references)

## Overview

DeepImpact uses computational and deep learning methods to gauge the societal impact of fundamental scientific
discoveries by analyzing comments and discussions in online news articles.

The project scrapes data from news websites, extracts user comments, and processes them using natural language
processing techniques to analyze public perception and impact of scientific topics.

Currently, DeepImpact supports the following news websites:

- BBC (www.bbc.co.uk)
- The Guardian (www.theguardian.com)
- Daily Mail (www.dailymail.co.uk)

Instructions on how to add support for new news sites are found [here](extend-website-readme.md).

## Features

- Automated scraping of HTML containing comments and other data from news sites (BBC, The Guardian, Daily Mail)
- Configurable scraping process via YAML configuration files
- SQL database management for tracking URLs and scraped content
- Processing pipeline to extract and analyze comment data

## Project Structure

```
DeepImpact/
├── configs/                           # Website-specific configuration files
│   ├── bbc.yaml                       # Configuration for BBC website
│   ├── dailymail.yaml                 # Configuration for Daily Mail website
│   └── guardian.yaml                  # Configuration for The Guardian website
├── db/                                # Database files
│   ├── create_initial_database.ipynb  # Notebook used for initial database creation
│   └── database.db                    # SQLite database with website URLs
├── scraped_html/                      # Directory for storing scraped HTML files
│   └── {table_name}/                  # Subdirectories for each database table
├── processed_comments/                # Directory for storing processed comments
│   └── {table_name}/                  # Subdirectories for each database table
├── scrapers/                          # Scraper modules
│   ├── __init__.py                    # Package initialization
│   ├── base.py                        # Base scraper class
│   ├── config.py                      # Configuration handling
│   ├── database.py                    # Database operations
│   ├── factory.py                     # Scraper factory pattern
│   ├── logger_setup.py                # Logging configuration
│   ├── utils.py                       # Utility functions
│   └── sites/                         # Site-specific scrapers
│       ├── __init__.py                # Package initialization
│       ├── default.py                 # Default scraper implementation
│       └── guardian.py                # Guardian-specific scraper
├── scrape_html.py                     # Script for scraping HTML
├── parse_html.py                      # Script for parsing HTML with LLM
├── requirements.txt                   # Required Python packages
├── .env                               # Environment file
└── .gitignore                         # Git ignore file
```

## Installation

### Prerequisites

- [Anaconda](https://docs.conda.io/projects/conda/en/stable/) installed
- Python 3.12
- Mac or Linux environment recommended

### Setup Instructions

1. Clone the repository:
   ```bash
   git clone https://github.com/username/DeepImpact.git
   cd DeepImpact
   ```
2. Create and activate a conda environment:
   ```bash
   conda create -n DeepImpact python=3.12
   conda activate DeepImpact
   ```
3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```
4. Install Playwright browsers:
   ```bash
   playwright install
   ```
5. Add API keys using a `.env` file

    - Create a new `.env` file in the project root:
        ```bash
        touch .env
        ```
    - Add your API keys

      Open the `.env` file in your preferred editor and add your keys using the format:

        ```
        KEY_NAME=your_api_key_here
        ANOTHER_KEY=another_api_key_here
        ```
    - Example:
        ```
        OPENAI_API_KEY=sk-abc123yourkey
        CLAUDE_API_KEY=claude-456defkey
        ```

      > 💡 Do **not** wrap the values in quotes unless required for escaping special characters.

### Optional - Installing Ollama

If you want to use Ollama and a local LLM when parsing scraped HTML, you can install it as follows:

1. Visit the [Ollama website](https://ollama.com) and download the installer for your operating system.

2. Follow the installation guide specific to your platform.

3. Once installed, verify the installation by running the following command in your terminal:
   ```bash
   ollama --version
   ```
   This should output the installed version of Ollama. If it fails, you may need to start the Ollama application.

4. Download a model e.g. Llama3.2
   ```bash
   ollama pull llama3.2
   ```

## Usage

### Database Setup

The database is an SQLite database located at `db/database.db` and contains tables for different scientific topics. Each
table includes:

- Article URLs from news sites
- Site information e.g. BBC, The Guardian, Daily Mail (must match with entries in `scrapers/factory.py`)
- Target scientific topic
- Scraping configuration name (must match a YAML dictionary name in `configs/*.yaml`)
- Paths to scraped HTML files
- Timestamps for scraping operations

A useful programme for viewing SQLite databases is `DB Browser for SQLite` which can be found
[here](https://sqlitebrowser.org).

Before scraping, you need to set up the database with the articles you want to analyze.
An initial database has been created by running `db/create_initial_database.ipynb`.

To add a single new record to the database you can use

```python
from scrapers.database import WebArchiveDB

db = WebArchiveDB(db_path='db/database.db', db_table_name='your_table_name')

new_entry = {
    'site': 'Your Site',  # Must match the key in SITE_TO_CONFIG
    'url': 'https://www.your-site.com/article-with-comments',
    'target': 'Scientific Topic',  # The scientific topic being discussed
    'scraping_config': 'your_site_cfg0'  # Config name from your YAML file
}

db.add_to_database(new_entry)
```

Adding multiple records can be done with a simple loop over a list of URLs.

### Step 1: Scraping News Articles

To scrape HTML from news websites:

```bash
python scrape_html.py --table TABLE_NAME
```

Where `TABLE_NAME` is the name of a table in the database. For example:

```bash
python scrape_html.py --table guardian_proxima_b
```

The script will:

1. Connect to the database and retrieve URLs from the specified table
2. Load the appropriate site configuration (BBC, Guardian, Daily Mail)
3. Navigate to each URL and extract the HTML content with comments
4. Save the raw HTML to the `scraped_html/{table_name}/` directory
5. Update the database with file paths and scraping timestamps

### Step 2: Processing Comments

After scraping, use the parsing script to extract and process the comments:

```bash
python parse_html.py --table TABLE_NAME
```

This will:

- Open each HTML file path stored in the specified table
- Use the ScrapeGraphAI package to send the HTML to a LLM for processing and extraction of comments and other relevant data
- Save the processed comments and other data to the `processed_comments/TABLE_NAME/` directory

## Configuration

The project uses YAML files in the `configs/` directory to define scraping parameters for each supported news site.

### Site-Specific Configurations

Each website has its own configuration file with selectors for:

- Cookie consent dialogs
- Comment sections
- "Load more comments" buttons
- Pagination controls

For example, to configure the BBC scraper:

```yaml
# configs/bbc.yaml
bbc_cfg0:
  accept_cookies_selector:
    test_id: accept-button
  expose_initial_comments_selector:
    label: 'View comments'
  more_comments_selectors:
    - role: button
      name: More comments
    - role: button
      name: 'More replies (\d+)'
  comments_container_selector:
    test_id: 'comments-container'
```

## Supported News Sites

### BBC (www.bbc.co.uk)

- Standard implementation using the `DefaultScraper` class
- Configured to handle BBC's comment system and cookie consent dialogs

### The Guardian (www.theguardian.com)

- Custom implementation using the `GuardianScraper` class
- Handles The Guardian's specific comment threading and pagination system

### Daily Mail (www.dailymail.co.uk)

- Standard implementation using the `DefaultScraper` class
- Configured to handle Daily Mail's comment system and cookie consent dialogs

## How It Works

1. **Database Management**: The `WebArchiveDB` class in `scrapers/database.py` manages an SQLite database containing
   URLs and metadata.

2. **Scraper Factory**: The `ScraperFactory` class in `scrapers/factory.py` creates the appropriate scraper for each
   news site.

3. **HTML Scraping**: The scraper:
    - Navigates to the URL
    - Accepts cookies using the configured selectors
    - Clicks buttons to load comments
    - Extracts the HTML from the comments container

4. **Comment Processing**: The parser:
    - Reads the saved HTML files
    - Uses an LLM to extract and structure comments
    - Saves the processed data for analysis


## References

[1] White, C.D., Phillips, A. and Sajonia-Coburgo-Gotha, B. (2022) 'Retrospectively evidencing research impact using
online data mining'. Research for All, 6 (1), 7, 1–17. DOI: https://doi.org/10.14324/RFA.06.1.07.
