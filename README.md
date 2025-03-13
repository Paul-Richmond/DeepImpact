# DeepImpact

## Overview
DeepImpact is a project that uses computational and deep learning methods to gauge the societal impact of 
fundamental scientific discoveries. 
The proof of concept for this approach is described in the paper [[1]](#references).

Currently, DeepImpact is in an early stage and scrapes data from a limited set of news websites:
- www.bbc.co.uk
- www.theguardian.com
- www.dailymail.co.uk

## Installation

### Prerequisites
- [Anaconda](https://docs.conda.io/projects/conda/en/stable/) installed on a Mac machine

### Setup Instructions
1. Clone the repository:
   ```bash
   git clone https://github.com/Paul-Richmond/DeepImpact.git
   cd DeepImpact
   ```

2. Create a new conda environment:
   ```bash
   conda env create -n DeepImpact python=3.12
   ```

3. Activate the environment and install required packages:
   ```bash
   conda activate DeepImpact
   pip install -r requirements.txt
   ```

4. Install Playwright browsers:
   ```bash
   playwright install
   ```

## Database Structure

The project uses an SQLite database located at `db/database.db`, created 
using the `create_initial_database.ipynb` notebook. The database contains 
several tables, each corresponding to news articles related to a 
specific scientific topic (e.g., BBC News articles about the Cassini space probe).

Each table includes URLs to relevant news articles and their associated metadata. 
After running the scraping process, file paths to the scraped HTML and processed 
comments are automatically added to the tables.

## Usage

### Step 1: Scrape HTML from News Websites
Use the Playwright automation tool to extract comments and save the resulting HTML:

```bash
python3 scrape_html.py --table TABLE_NAME
```

Where `TABLE_NAME` is a table in the database. This command will:
- Visit each URL in the specified table
- Extract the HTML content, including user comments
- Save the raw HTML to the `scraped_html` folder
- Update the database with the file paths

### Step 2: Process Comments with LLM
Use ScrapeGraphAI to process the HTML through a Language Learning Model:

```bash
python3 parse_html.py --table TABLE_NAME
```

This command will:
- Open each HTML file path stored in the specified table
- Send the content to an LLM for processing
- Extract comments and other relevant data
- Save the processed comments to the `processed_comments` folder

## Project Structure
```
DeepImpact/
├── db/
│   └── database.db             # SQLite database with website URLs
├── scraped_html/               # Raw HTML files from websites
├── processed_comments/         # Extracted comments after LLM processing
├── create_initial_database.ipynb  # Notebook for database creation
├── scrape_html.py              # Script for HTML scraping
├── parse_html.py               # Script for LLM-based HTML parsing
└── requirements.txt            # Required Python packages
```

## References
<a id="references"></a>
[1] White, C.D., Phillips, A. and Sajonia-Coburgo-Gotha, B. (2022) 
'Retrospectively evidencing research impact using online data mining'. 
Research for All, 6 (1), 7, 1–17. DOI: https://doi.org/10.14324/RFA.06.1.07.
