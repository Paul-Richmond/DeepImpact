import argparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException
from selenium.webdriver.support.wait import WebDriverWait
from bs4 import BeautifulSoup
import pandas as pd
from utils.helpers import setup_driver
from utils.io import load_config_yaml, export_output


class BbcComments:
    def __init__(self, driver, webdriverwait, cfg):
        self.driver = driver
        self.wait = webdriverwait
        self.cfg = cfg

    def scrape(self, url):

        # We check if the url endswith '#comments' and append it if it doesn't.
        # We do this because BBC News urls that end with '#comments' automatically
        # expose the first comments removing the need to click on the 'View Comments' button
        if not url.endswith('#comments'):
            url += '#comments'

        self.load_website(url)

        # found that there is only one iframe in the html which happens
        # to contain all the elements we need to interact with
        self.wait.until(EC.frame_to_be_available_and_switch_to_it((By.TAG_NAME, 'iframe')))

        '''check for presence of 'These comments are now closed.'
        If it is there we can keep on pressing the 'More comments' button.
        Otherwise we will see the 'Check for new replies button'
        which can be pressed infinitely. Alternative is 'Sign in to comment, reply and react'''
        try:
            self.driver.find_element(By.XPATH, self.cfg['bbc_site']['comments_closed'])
            closed = True
        except NoSuchElementException:
            closed = False

        # Repeatedly click on the 'More comments' button until it disappears
        try:
            more_comments_button = self.wait.until(EC.presence_of_element_located((By.XPATH,
                                                                                   self.cfg['bbc_site'][
                                                                                       'more_comments_button'])))
            self.driver.execute_script("arguments[0].click();", more_comments_button)
            button_exists = True
            button_clicks = 1
            print(f'Clicked "More comments" button.')
        except NoSuchElementException:
            button_exists = False

        while button_exists:
            try:
                more_comments_button = self.wait.until(EC.presence_of_element_located((By.XPATH,
                                                                                       self.cfg['bbc_site'][
                                                                                           'more_comments_button'])))
                self.driver.execute_script("arguments[0].click();", more_comments_button)
                button_clicks += 1
                print(f'Clicked "More comments" button {button_clicks} times.')
            except TimeoutException:
                print('Finished clicking "More comments" button.')
                button_exists = False
            except WebDriverException as e:
                print('Something went wrong trying to click "More comments" button.')
                print(e)
                button_exists = False

        # why isn't this working after the 13th button?
        loc_child = ((By.XPATH, '''//button[@class="reply-more-replies__button"]
        //span[@class="reply-more-replies__text"]'''))
        keep_clicking = True
        while keep_clicking:
            try:
                mrb = self.wait.until(EC.presence_of_element_located((By.XPATH,
                                                                      self.cfg['bbc_site']['more_replies_button'])))
                button_text = mrb.text.rstrip('\ndown')
                self.driver.execute_script("arguments[0].click();", mrb)
                self.wait.until_not(EC.text_to_be_present_in_element(loc_child, button_text))
            except WebDriverException:
                keep_clicking = False

        # We've now exposed all the html elements we need to parse the html and extract
        data = self.parse_html()

        # place the scraped data into a DataFrame
        df = pd.DataFrame(data, columns=self.cfg['df_columns'])
        self.driver.quit()  # close the webdriver

        return df

    def load_website(self, url):
        self.driver.get(url)

    def click_button(self, selector):
        if selector.startswith('//'):
            locator = (By.XPATH, selector)
        else:
            locator = (By.CLASS_NAME, selector)

        try:
            self.driver.find_element(*locator).click()
            return True
        except NoSuchElementException:
            try:
                button = self.wait.until(EC.presence_of_element_located(locator))
                ActionChains(self.driver).click(button).perform()
                return True
            except TimeoutException:
                return False

    def parse_html(self):
        bs = BeautifulSoup(self.driver.page_source, 'html.parser')
        # BeautifulSoup can't handle xpaths, so we have to use class names instead
        contents = bs.find_all('div', class_=self.cfg['bbc_site']['comment_contents'])

        data = [[content.findChild('div', selector).text for selector in self.cfg['data_selectors']]
                for content in contents]
        return data


def get_bbc_comments(run_args):
    config = load_config_yaml(run_args.config)

    driver_args = config['ChromeOptions']
    webdriverwait_args = config['WebDriverWait'].values()
    url = config['target_url']
    config_site = config['site']

    driver = setup_driver(driver_args)
    webdriverwait = WebDriverWait(driver, *webdriverwait_args)

    df = BbcComments(driver, webdriverwait, config_site).scrape(url)
    export_output(args.output, df)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Configuration file", required=True)
    parser.add_argument("-o", "--output", help="Output file", required=True)
    args = parser.parse_args()

    get_bbc_comments(args)
