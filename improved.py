import re
from playwright.sync_api import Playwright, sync_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import date
from urllib.parse import urlparse
from typing import Dict, List, Optional
from dataclasses import dataclass

DEBUG = True


@dataclass
class SiteConfig:
    """Configuration for each news site's comment section"""
    site_code: str
    view_comments_selector: Optional[dict] = None
    more_comments_selectors: List[dict] = None
    comments_container_selector: dict = None
    accept_cookies_selector: Optional[dict] = None

    def get_container_html(self, page) -> str:
        """Get the HTML content of the comments container"""
        if 'test_id' in self.comments_container_selector:
            return page.get_by_test_id(self.comments_container_selector['test_id']).inner_html()
        elif 'label' in self.comments_container_selector:
            return page.get_by_label(self.comments_container_selector['label']).inner_html()
        elif 'id' in self.comments_container_selector:
            return page.locator(self.comments_container_selector['id']).inner_html()
        raise ValueError("Invalid container selector configuration")


# Site-specific configurations
SITE_CONFIGS: Dict[str, SiteConfig] = {
    'www.bbc.co.uk': SiteConfig(
        site_code='bbc',
        view_comments_selector={'label': 'View comments'},
        more_comments_selectors=[
            {'role': 'button', 'name': 'More comments'},
            {'role': 'button', 'name': 'More replies'}
        ],
        comments_container_selector={'test_id': 'comments-container'}
    ),
    # 'www.dailymail.co.uk': SiteConfig(
    #     site_code='dm',
    #     accept_cookies_selector={'role': 'button', 'name': 'Accept'},
    #     more_comments_selectors=[
    #         {'label': re.compile(r"Show more(?:\s+comments)?")},
    #         {'label': re.compile(r"(?:Show more|See all)\s+replies")},
    #         {'text': 'See more'}
    #     ],
    #     comments_container_selector={'label': 'List of Comments'}
    # )
    'www.dailymail.co.uk': SiteConfig(
        site_code='dm',
        accept_cookies_selector={'role': 'button', 'name': 'Accept'},
        more_comments_selectors=[
            {'label': re.compile(r"Show more(?:\s+comments)?")},
            {'label': re.compile(r"(?:Show more|See all)\s+replies")},
            {'text': 'See more'}
        ],
        comments_container_selector={'id': '#reader-comments'}
    )
}


def write_raw_html_to_file(raw_html: str, filename: str) -> None:
    """Write HTML content to a file"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(raw_html)
    print(f"Raw HTML content has been written to {filename}")


def get_filename_from_url(site_code: str, url: str) -> str:
    """Generate filename from URL"""
    url_parse = urlparse(url)
    return f"{site_code}{url_parse.path.replace('/', '_')}.html"


def click_button_until_gone(page, selector: dict, timeout: int = 10000) -> None:
    """Click a button repeatedly until it's no longer available"""
    while True:
        try:
            if 'label' in selector:
                button = page.get_by_label(selector['label'])
            elif 'role' in selector and 'name' in selector:
                button = page.get_by_role(selector['role'], name=selector['name'])
            elif 'text' in selector:
                button = page.get_by_text(selector['text'])
            else:
                raise ValueError(f"Invalid selector configuration: {selector}")

            button.first.click(timeout=timeout)
        except PlaywrightTimeoutError:
            break


def scrape_comments(playwright: Playwright, url: str, filename: str) -> None:
    """Main function to scrape comments from supported news sites"""
    domain = urlparse(url).netloc
    if domain not in SITE_CONFIGS:
        raise ValueError(f"Unsupported site: {domain}")

    config = SITE_CONFIGS[domain]

    headless_mode = not DEBUG
    browser = playwright.chromium.launch(headless=headless_mode)
    context = browser.new_context()
    page = context.new_page()

    try:
        page.goto(url)

        # Handle cookie consent if needed
        if config.accept_cookies_selector:
            click_button_until_gone(page, config.accept_cookies_selector)

        # View comments if needed
        if config.view_comments_selector:
            click_button_until_gone(page, config.view_comments_selector)

        # Click all configured "more" buttons
        if config.more_comments_selectors:
            for selector in config.more_comments_selectors:
                click_button_until_gone(page, selector)

        # Get and save HTML content
        html_content = config.get_container_html(page)
        write_raw_html_to_file(html_content, filename)

    finally:
        context.close()
        browser.close()


def main(url: str) -> None:
    """Entry point for the scraper"""
    domain = urlparse(url).netloc
    if domain not in SITE_CONFIGS:
        raise ValueError(f"Unsupported site: {domain}")

    filename = get_filename_from_url(SITE_CONFIGS[domain].site_code, url)

    with sync_playwright() as playwright:
        scrape_comments(playwright, url, filename)


if __name__ == "__main__":
    urls = ["https://www.bbc.co.uk/sport/cricket/68128995",
            "https://www.bbc.co.uk/news/articles/c0qwvppk0zzo",
            "https://www.dailymail.co.uk/sciencetech/article-7138333/Origins-Saturns-rings-uncovered-thanks-data-NASAs-Cassini-probe",
            "https://www.dailymail.co.uk/sciencetech/article-4556178/Cassini-sends-stunning-image-ripples-Saturn-s-ring"]
    url = urls[3]
    main(url)
