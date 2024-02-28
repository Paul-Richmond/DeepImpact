from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.support.wait import WebDriverWait
from bs4 import BeautifulSoup
import pandas as pd
# from tqdm import trange
from utils.helpers import setup_driver


class Site:
    def __init__(self, url, cfg):
        self.url = url
        self.cfg = cfg
        self.driver = setup_driver()
        self.wait = WebDriverWait(self.driver, 1.5)

    def load_website(self, url):
        self.driver.get(url)

    def find_element(self, selector):
        try:
            return self.wait.until(EC.presence_of_element_located((By.XPATH, selector)))
        except TimeoutException:
            return None

    def find_elements(self, selector):
        try:
            return self.wait.until(EC.presence_of_all_elements_located((By.XPATH, selector)))
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

        data = []
        for content in contents:
            sub_data = []
            for selector in self.cfg['data_selectors']:
                try:
                    sub_data.append(content.findChild('div', selector).text)
                except AttributeError:
                    sub_data.append(None)
            data.append(sub_data)

        return data

    def data_to_dataframe(self, data):
        return pd.DataFrame(data, columns=self.cfg['df_columns'])


class Bbc(Site):
    def __init__(self, url, cfg):
        super().__init__(url, cfg)

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

        df = self.data_to_dataframe(data)  # place the scraped data into a DataFrame
        self.driver.quit()  # close the webdriver

        return df


class Guardian(Site):
    def __init__(self, url, cfg):
        super().__init__(url, cfg)

    def scrape(self):
        if not self.url.endswith('#comments'):
            self.url += '#comments'

        self.load_website(self.url)

        self.accept_cookies()  # get rid of the "It's your choice" pop-up window

        data = []

        pages_control_element = self.find_element(self.cfg['pages']['page_control_element'])
        try:
            page_control = pages_control_element.find_element(By.XPATH, self.cfg['pages']['page_forward_button'])
        except NoSuchElementException:
            page_control = pages_control_element.find_elements(By.XPATH, self.cfg['pages']['page_numbered_buttons'])

        if isinstance(page_control, list):
            for page_button in page_control:
                page_button.click()
                self.wait.until(EC.presence_of_element_located((By.XPATH, self.cfg['pages']['comments_column'])))
                self.expand_more_replies()
                page_data = self.parse_html()
                data.extend(page_data)
        else:
            # parse page 1
            self.expand_more_replies()
            page_data = self.parse_html()
            data.extend(page_data)
            while True:  # keep on clicking the page forward button
                try:
                    page_control.click()
                    self.wait.until(EC.presence_of_element_located((By.XPATH, self.cfg['pages']['comments_column'])))
                    self.expand_more_replies()
                    page_data = self.parse_html()
                    data.extend(page_data)
                except StaleElementReferenceException:
                    break

        df = self.data_to_dataframe(data)  # place the scraped data into a DataFrame
        self.driver.quit()  # close the webdriver

        return df

    def expand_more_replies(self):
        while True:  # expand all the 'show x more reply/replies' button
            button = self.find_element(self.cfg['pages']['more_replies_button'])
            if button is not None:
                self.click_button(button)
            else:
                break

    def accept_cookies(self):
        # this code clicks the accept cookies button
        self.wait.until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, self.cfg['cookies']['iframe'])))
        accept_cookies = self.find_element(self.cfg['cookies']['accept_button'])
        self.click_button(accept_cookies)
        self.driver.switch_to.parent_frame()


class DailyMail(Site):
    def __init__(self, url, cfg):
        super().__init__(url, cfg)

    def scrape(self):
        if not self.url.endswith('#comments'):
            self.url += '#comments'

        self.load_website(self.url)
