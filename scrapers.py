from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.wait import WebDriverWait
from bs4 import BeautifulSoup
import pandas as pd
from utils.helpers import setup_driver


class Bbc:
    def __init__(self, url, cfg):
        self.url = url
        self.cfg = cfg
        self.driver = setup_driver()
        self.wait = WebDriverWait(self.driver, 3)

    def scrape(self):
        # We check if the url endswith '#comments' and append it if it doesn't.
        # We do this because BBC News urls that end with '#comments' automatically
        # expose the first comments removing the need to click on the 'View Comments' button
        if not self.url.endswith('#comments'):
            self.url += '#comments'

        self.load_website(self.url)

        # found that there is only one iframe in the html which happens
        # to contain all the elements we need to interact with
        self.wait.until(EC.frame_to_be_available_and_switch_to_it((By.TAG_NAME, 'iframe')))

        clickables = [self.cfg['control']['more_comments_button'], self.cfg['control']['more_replies_button']]

        for selector in clickables:
            while True:
                button = self.find_element(selector)
                if button is not None:
                    self.click_button(button)
                else:
                    break

        # We've now exposed all the html elements we need to parse the html and extract
        data = self.parse_html()

        # place the scraped data into a DataFrame
        df = pd.DataFrame(data, columns=self.cfg['df_columns'])
        self.driver.quit()  # close the webdriver

        return df

    def load_website(self, url):
        self.driver.get(url)

    def find_element(self, selector):
        try:
            return self.wait.until(EC.presence_of_element_located((By.XPATH, selector)))
        except TimeoutException:
            return None

    def click_button(self, button):
        try:
            self.driver.execute_script("arguments[0].click();", button)
            self.wait.until(EC.staleness_of(button))
        except TimeoutException:
            pass

    def parse_html(self):
        bs = BeautifulSoup(self.driver.page_source, 'html.parser')
        # BeautifulSoup can't handle xpaths, so we have to use class names instead
        contents = bs.find_all('div', class_=self.cfg['data_container'])

        data = [[content.findChild('div', selector).text for selector in self.cfg['data_selectors']]
                for content in contents]
        return data
