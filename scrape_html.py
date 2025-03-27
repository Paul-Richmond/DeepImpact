from playwright.sync_api import sync_playwright

from scrapers import scrape_comments_html
from scrapers.database import WebArchiveDB
from scrapers.utils import parse_arguments

SITE_TO_CONFIG = {"Daily Mail": "./configs/dailymail.yaml",
                  "The Guardian": "./configs/guardian.yaml",
                  "BBC": "./configs/bbc.yaml"}


if __name__ == "__main__":
    # Parse command line arguments
    args = parse_arguments()
    # Setup database connection
    db = WebArchiveDB(db_path='db/database.db', db_table_name=args.table)
    db_entries = db.execute_query(f'''SELECT * FROM {db.db_table_name}''')

    for entry in db_entries:
        idx = entry['id']
        site = entry['site']
        url = entry['url']
        cfg_name = entry['scraping_config']

        filename = f'scraped_html/{db.db_table_name}/id_{idx}.html'

        with sync_playwright() as playwright:
            html_content = scrape_comments_html(playwright=playwright,
                                                url=url,
                                                site_type=site,
                                                config_path=SITE_TO_CONFIG[site],
                                                config_name=cfg_name,
                                                output_path=filename,
                                                headless=False
                                                )

        db.add_scrape_file_and_time(filename, idx)
