# Extending DeepImpact

## Overview
This guide explains how to extend the DeepImpact project by either adding support for a 
new news website or adding a new configuration for an existing website.


## Steps to Add a New Website

### 1. Create a Configuration File

Create a new YAML file in the `configs/` directory (e.g., `configs/your-site.yaml`). 
This file defines the selectors used to navigate and extract data from the website.

```yaml
your_site_cfg0:
  # Optional: Frame selector for sites with iframes (like cookie consent dialogs)
  switch_to_frame_selector:
    iframe: "Cookie Consent Frame"
  
  # Selector for the cookie consent button
  accept_cookies_selector:
    role: "button"
    name: "Accept All"
  
  # Selector for revealing initial comments (if needed)
  expose_initial_comments_selector:
    role: "button"
    name: "Show Comments"
  
  # List of selectors for loading more comments
  more_comments_selectors:
    - role: button
      name: "Load More Comments"
    - role: button
      name: !!python/object/apply:re._compile
        - 'Show (\d+) more repl(?:y|ies)'
        - 34  # 34 means use re.IGNORECASE
  
  # Selector for the container that holds all comments and associated metadata
  comments_container_selector:
    id: "#comments-section"
```

Notes on selector types:
- `role`: Uses Playwright's role-based selectors (button, link, etc.)
- `id`: CSS selector for element IDs
- `label`: Text label selectors
- `test_id`: For elements with data-testid attributes
- `iframe`: For selecting iframes by title

You can use regular expressions by using the `!!python/object/apply:re._compile` syntax.
A useful website for checking regex expressions can be found [here](https://regex101.com).


### 2. Create a Custom Scraper (Optional)

For most websites, the `DefaultScraper` should work fine. However, if your website 
has unique requirements, you can create a custom scraper (e.g. see the `GuardianScraper` class):

1. Create a new file in `scrapers/sites/` (e.g., `your_site.py`):

```python
import logging
from typing import Optional

from playwright.sync_api import Playwright

from ..base import BaseScraper
from ..utils import browser_context, click_button_until_gone, get_iframe, click_button

logger = logging.getLogger(__name__)

class YourSiteScraper(BaseScraper):
    """Scraper implementation for Your Site"""

    def scrape(self, playwright: Playwright, url: str, headless: bool = False, max_pages: Optional[int] = None) -> str:
        logger.info(f'Starting Your Site web scraping for URL: {url}')

        try:
            with browser_context(playwright, headless) as page:
                page.goto(url)
                html_content = []

                # Handle cookie consent
                if self.config.accept_cookies_selector:
                    logger.info('Accepting cookies')
                    click_button_until_gone(page, self.config.accept_cookies_selector)

                # Site-specific handling here...
                
                # Get comments container HTML
                html_content.append(self.config.get_container_html(page))

        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            raise

        logger.info('Completed web scraping')
        return ''.join(html_content)
```

2. Register your custom scraper and configuration file in `scrapers/factory.py`:

```python
from .sites.your_site import YourSiteScraper

class ScraperFactory:
    """Factory class to create appropriate scrapers based on website"""

    _scrapers: Dict[str, Type[BaseScraper]] = {
        "The Guardian": GuardianScraper,
        "Daily Mail": DefaultScraper,
        "BBC": DefaultScraper,
        "Your Site": YourSiteScraper,  # Add this line
        # Add more scrapers here as they are implemented
    }

    _site_configs: Dict[str, str] = {
        "The Guardian": "./configs/guardian.yaml",
        "Daily Mail": "./configs/dailymail.yaml",
        "BBC": "./configs/bbc.yaml",
        "Your Site": ".configs/your-site.yaml", # Add this line
        # Add more site configurations here as they are implemented
    }
```

### 4. Adapt SiteConfig and load_site_config (Optional)

If the new website requires entirely new automation that cannot be
facilitated in the existing setup, it may be necessary to extend the `SiteConfig` class
in `scrapers/config.py` by adding new attributes that correspond to entries in the new
configuration file.
Additionally, update the `load_site_config` function in the same file to handle the new
attributes and ensure they are properly initialized from the YAML configuration. Clearly
document any new attributes or methods added to the `SiteConfig` class for easier maintenance
and understanding of the codebase.


### 5. Add Entries to the Database

Use the `create_initial_database.ipynb` notebook or directly insert records into the database:

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

### 6. Add a Prompt (Optional)

If your website requires specific instructions for parsing its HTML structure, you can add a custom prompt 
to the `get_scraping_prompt` function in `parse_html.py`.
Customize the prompt to reflect the specific HTML structure and data format of 
your target website. Include any unique characteristics or challenges that would help the 
parser extract the correct information.



### 7. Test Your Implementation

Run the scraping process with your new table:

```bash
python3 scrape_html.py --table your_table_name
```

and then the parsing process

```bash
python3 parse_html.py --table your_table_name
```

## Steps to Add a New Configuration for an Existing Website

If, for instance, the BBC redesigns its news website so that the existing YAML configuration file
no longer locates the objects needed to automate the HTML scraping correctly, 
you can add a new configuration as follows:

### 1. Update the Configuration File

Open the existing YAML file (e.g., `configs/bbc.yaml`) and append a new dictionary with updated selectors:

```yaml
# New configuration for updated website
bbc_cfg1:
  # Add all updated selectors here
  accept_cookies_selector:
    # New
  expose_initial_comments_selector:
    # New
  more_comments_selectors: 
    # New list
  comments_container_selector:  
    # New
  
# Existing configuration (still available for backward compatibility)
bbc_cfg0:
  accept_cookies_selector:
    test_id: accept-button
  .
  .
  .
```

### 2. Add Entries to the Database

Use the `create_initial_database.ipynb` notebook or directly insert records into the database:

```python
from scrapers.database import WebArchiveDB

db = WebArchiveDB(db_path='db/database.db', db_table_name='your_table_name')

new_entry = {
    'site': 'BBC', 
    'url': 'https://www.bbc.co.uk/news/article-with-comments',
    'target': 'Scientific Topic',  # The scientific topic being discussed
    'scraping_config': 'bbc_cfg1'  # New config name
}

db.add_to_database(new_entry)
```

### 3. Test Your Implementation

Run the scraping process with your new table:

```bash
python3 scrape_html.py --table your_table_name
```

## Selector Configuration Tips

1. **Inspect Elements**: Use Playwright's Inspector [tool](https://playwright.dev/python/docs/codegen) to identify the right selectors for your website.

2. **Cookies & Consent**: Many news sites have cookie consent banners. Make sure to handle them in your configuration.

3. **Comment Loading**: Some sites load comments dynamically. Use the `more_comments_selectors` to click "Load More" buttons until all comments are visible.

4. **Regular Expressions**: For buttons with variable text (like "Show 5 more replies"), use regex patterns.

5. **Comments Container**: Try to identify a container which has the least HTML as this will be passed to an LLM for parsing.


