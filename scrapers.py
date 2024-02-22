from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.wait import WebDriverWait
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm
from utils.helpers import setup_driver


class Site:
    def __init__(self, url, cfg):
        self.url = url
        self.cfg = cfg
        self.driver = setup_driver()
        self.wait = WebDriverWait(self.driver, 10)

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

        # place the scraped data into a DataFrame
        df = pd.DataFrame(data, columns=self.cfg['df_columns'])
        self.driver.quit()  # close the webdriver

        return df


class Guardian(Site):
    def __init__(self, url, cfg):
        super().__init__(url, cfg)

    def scrape(self):
        if not self.url.endswith('#comments'):
            self.url += '#comments'

        self.load_website(self.url)

        # this code clicks the accept cookies button
        self.wait.until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, self.cfg['cookies']['iframe'])))
        accept_cookies = self.find_element(self.cfg['cookies']['accept_button'])
        self.click_button(accept_cookies)
        self.driver.switch_to.parent_frame()

        # Focus on the three dropdown elements "Sort by", "Per page" and "Display threads"
        dropdowns = self.find_elements(self.cfg['dropdown']['dropdown_buttons'])
        dropdowns[2].click()  # this clicks the "Display threads" dropdown
        unthread = self.find_element(self.cfg['dropdown']['unthreaded'])  # select "Unthreaded" element
        self.click_button(unthread)  # click "Unthreaded" element

        # this code works out how many pages of comments there are
        # first we need the number of comments
        num_com_str = self.driver.find_element(By.XPATH, self.cfg['pages']['comments_number']).text
        num_com_list = num_com_str.split()
        num_com = int(num_com_list[-1])
        # then we need the comments displayed per page
        per_page = int(dropdowns[1].text)
        # now we work out how many pages we expect in addition to page 1
        if num_com % per_page == 0:
            num_addn_pages = int(num_com / per_page - 1)
        else:
            num_addn_pages = num_com // per_page  # this is automatically an int

        # Find the comments page selection elements
        # check button with class dcr-9boz50 exists, there will be 4 if
        # they do exist. The 2nd (and 4th) are the ones we want to go to next page
        # if it doesn't then we get a list of the page buttons
        page_controls = self.find_elements(self.cfg['pages']['page_control'])
        if page_controls:  # we have a non-empty list
            page_buttons = page_controls[1]
        else:
            page_buttons = self.find_element(self.cfg['pages']['page_control2']).find_elements(By.TAG_NAME,
                                                                                               'button')
        final_data = []
        # we get the comments on page 1
        data = self.parse_html()
        final_data.extend(data)

        # loop through all the pages of comments
        for page in tqdm(range(1, 1 + num_addn_pages)):
            if isinstance(page_buttons, list):
                self.click_button(page_buttons[page])
            else:
                self.click_button(page_buttons)
                page_buttons = self.find_elements(self.cfg['pages']['page_control'])[1]
            data = self.parse_html()
            final_data.extend(data)

        # place the scraped data into a DataFrame
        df = pd.DataFrame(final_data, columns=self.cfg['df_columns'])
        self.driver.quit()  # close the webdriver

        return df


class DailyMail(Site):
    def __init__(self, url, cfg):
        super().__init__(url, cfg)

    def scrape(self):
        if not self.url.endswith('#comments'):
            self.url += '#comments'

        self.load_website(self.url)
