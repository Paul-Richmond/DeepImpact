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
        # self.wait.until(EC.frame_to_be_available_and_switch_to_it((By.TAG_NAME, 'iframe')))

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

    def parse_html(self):
        bs = BeautifulSoup(self.driver.page_source, 'html.parser')
        # BeautifulSoup can't handle xpaths, so we have to use class names instead
        contents = bs.find_all('div', class_=self.cfg['data_container'])

        data = []
        for content in contents:
            sub_data = []
            for selector in self.cfg['data_selectors']:
                try:
                    sub_data.append(content.find(**selector).text)
                except AttributeError:
                    sub_data.append(None)
            data.append(sub_data)

            replies = content.find_all(**self.cfg['reply'])
            if replies is not None:
                for reply in replies:
                    sub_data = []
                    for selector in self.cfg['reply_selectors']:
                        try:
                            sub_data.append(reply.find(**selector).text)
                        except AttributeError:
                            sub_data.append(None)
                    data.append(sub_data)

        return data

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
        self.sr = None
        super().__init__(url, cfg)

    def scrape(self):
        if not self.url.endswith('#comments'):
            self.url += '#comments'

        self.load_website(self.url)

        self.decline_cookies()

        self.sr = self.get_shadow_root()

        self.expand_show_more_comments()
        self.expand_more_replies()
        self.expand_see_more()

        data = self.parse_html()
        df = self.data_to_dataframe(data)  # place the scraped data into a DataFrame
        self.driver.quit()  # close the webdriver

        return df

    def decline_cookies(self):
        cookie_window = self.find_element(self.cfg['cookies']['window'])
        self.click_button(cookie_window)
        reject_all_button = self.find_element(self.cfg['cookies']['reject_all'])
        self.click_button(reject_all_button)
        save_and_exit_button = self.find_element(self.cfg['cookies']['save_and_exit'])
        self.click_button(save_and_exit_button)

    def get_shadow_root(self):
        return self.find_element(self.cfg['control']['shadow_root']).shadow_root

    def expand_show_more_comments(self):
        while True:  # expand all the 'Show More Comments' button
            try:
                button = self.sr.find_element(By.CLASS_NAME,
                                              self.cfg['control']['more_comments_button'])
                self.click_button(button)
            except:
                break

    def expand_more_replies(self):
        while True:
            more_replies_buts = self.sr.find_elements(By.CLASS_NAME,
                                                      self.cfg['control']['show_more_replies'])
            if len(more_replies_buts) != 0:
                for but in more_replies_buts:
                    self.click_button(but)
            else:
                break

    def expand_see_more(self):
        while True:
            comment_blocks = self.sr.find_elements(By.CLASS_NAME,
                                                   self.cfg['control']['see_more'])
            buttons_clicked = 0
            for comment_block in comment_blocks:
                span_elements = comment_block.find_elements(By.CSS_SELECTOR, 'span')
                for span_element in span_elements:
                    if span_element.text == 'See more':
                        self.click_button(span_element)
                        buttons_clicked += 1
            if buttons_clicked == 0:
                break

    def parse_html(self):
        data_container = self.sr.find_element(By.CLASS_NAME, self.cfg['data_container'])
        html_of_interest = self.driver.execute_script('return arguments[0].innerHTML',
                                                      data_container)
        bs = BeautifulSoup(html_of_interest, 'html.parser')
        # BeautifulSoup can't handle xpaths, so we have to use class names instead
        contents = bs.find_all('div', class_=self.cfg['contents_container'])

        data = []
        for content in contents:
            sub_data = []
            for selector in self.cfg['data_selectors']:
                try:
                    sub_data.append(content.find(*selector).text)
                except AttributeError:
                    sub_data.append(None)
            data.append(sub_data)

        return data
