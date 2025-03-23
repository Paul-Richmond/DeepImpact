from playwright.sync_api import sync_playwright

from scrapers import scrape_site_html
from utils.io import WebArchiveDB


SITE_TO_CONFIG = {"Daily Mail": "../configs/dailymail.yaml",
                  "The Guardian": "../configs/guardian.yaml",
                  "BBC": "../configs/bbc.yaml"}


if __name__ == "__main__":
    testdata = [{'table_name': 'guardian_proxima_b', 'rows': '1,4,7'},
                {'table_name': 'guardian_cassini', 'rows': '1'},
                {'table_name': 'dm_cassini', 'rows': '1,21,29,32,52,63,73,83,94,114,135,146'},
                {'table_name': 'dm_proxima_b', 'rows': '1,12,24'},
                {'table_name': 'bbc_cassini', 'rows': '1'}]

    for data in testdata:
        # Setup database connection
        db = WebArchiveDB(db_path='../testing/database_test.db', db_table_name=data['table_name'])
        db_entries = db.execute_query(f'''SELECT * FROM {data['table_name']} WHERE ROWID IN ({data['rows']})''')

        for entry in db_entries:
            idx = entry['id']
            site = entry['site']
            url = entry['url']
            cfg_name = entry['scraping_config']

            filename = f'../testing/scraped_html/{data['table_name']}/id_{idx}.html'

            with sync_playwright() as playwright:
                html_content = scrape_site_html(playwright=playwright,
                                                url=url,
                                                site_type=site,
                                                config_path=SITE_TO_CONFIG[site],
                                                config_name=cfg_name,
                                                output_path=filename,
                                                headless=False
                                                )

            db.add_scrape_file_and_time(filename, idx)
