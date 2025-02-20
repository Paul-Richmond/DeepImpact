import re
from playwright.sync_api import Playwright, TimeoutError as PlaywrightTimeoutError
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class SiteConfig:
    """Configuration for each news site's comment section"""
    site_code: str
    accept_cookies_selector: Optional[dict] = None
    comments_order_selector: Optional[dict] = None
    expose_initial_comments_selector: Optional[dict] = None
    page_buttons_selector: Optional[dict] = None
    more_comments_selectors: List[dict] = None
    comments_container_selector: dict = None

    def get_container_html(self, page) -> str:
        """Get the HTML content of the comments container"""
        if 'test_id' in self.comments_container_selector:
            return page.get_by_test_id(self.comments_container_selector['test_id']).inner_html()
        elif 'label' in self.comments_container_selector:
            return page.get_by_label(self.comments_container_selector['label']).inner_html()
        elif 'id' in self.comments_container_selector:
            return page.locator(self.comments_container_selector['id']).inner_html()
        raise ValueError("Invalid container selector configuration")


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


def scrape_comments(playwright: Playwright, url: str, config: SiteConfig) -> str:
    """Main function to scrape comments from supported news sites"""
    print('Starting web scraping')
    browser = playwright.chromium.launch(headless=False)
    # Running in headless=True mode means that inner_html() doesn't return all the html
    # Seems to be a Playwright bug see https://github.com/microsoft/playwright/issues/12410
    context = browser.new_context()
    page = context.new_page()

    try:
        print(f'Attempting to open: {url}')
        page.goto(url)

        # Handle cookie consent if needed
        if config.accept_cookies_selector:
            print('Attempting to accept cookies')
            click_button_until_gone(page, config.accept_cookies_selector)

        # Expose initial comments if needed
        # this often exposes additional buttons to be clicked
        if config.expose_initial_comments_selector:
            print('Attempting to exposure initial comments')
            click_button_until_gone(page, config.expose_initial_comments_selector)

        # Click all configured "more" buttons
        if config.more_comments_selectors:
            print('Attempting to view more comments')
            for selector in config.more_comments_selectors:
                click_button_until_gone(page, selector)

        html_content = config.get_container_html(page)

        if config.page_buttons_selector:
            print('Attempting to control page buttons')
            num = 2
            while True:
                try:
                    print('Attempting to control next page')
                    page.locator('li').filter(has_text=re.compile(fr"^{num}$")).click(timeout=10000)
                    # Click all configured "more" buttons
                    if config.more_comments_selectors:
                        print('Attempting to view more comments')
                        for selector in config.more_comments_selectors:
                            click_button_until_gone(page, selector)

                    # Get and save HTML content
                    html_content += config.get_container_html(page)

                    num += 1
                except PlaywrightTimeoutError:
                    print('Reached end of control page buttons')
                    break

    finally:
        context.close()
        browser.close()

    print('Completed web scraping')

    return html_content
