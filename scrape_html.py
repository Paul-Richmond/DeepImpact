from playwright.sync_api import sync_playwright
from scrapers import scrape_comments, load_site_config, write_raw_html_to_file
from utils.io import WebArchiveDB


SITE_TO_CONFIG = {"Daily Mail": "./configs/dailymail.yaml",
                  "The Guardian": "./configs/guardian.yaml",
                  "BBC": "./configs/bbc.yaml"}


if __name__ == "__main__":
    db = WebArchiveDB(db_path='db/database.db', db_table_name='guardian_cassini')
    db_entries = db.execute_query(f'''SELECT * FROM {db.db_table_name}''')

    for entry in db_entries:
        idx = entry['id']
        site = entry['site']
        url = entry['url']
        cfg_name = entry['scraping_config']

        filename = f'scraped_html/{db.db_table_name}/id_{idx}.html'
        site_cfg = load_site_config(SITE_TO_CONFIG[site], cfg_name)

        with sync_playwright() as playwright:
            html_content = scrape_comments(playwright, url, site_cfg)

        write_raw_html_to_file(html_content, filename)
        db.add_scrape_file_and_time(filename, idx)
