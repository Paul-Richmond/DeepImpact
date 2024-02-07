import argparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException
from selenium.webdriver.support.wait import WebDriverWait
from bs4 import BeautifulSoup
import pandas as pd
from utils.helpers import setup_driver
from utils.io import load_config_yaml


class BbcComments:
    def __init__(self, driver, webdriverwait, cfg):
        self.driver = driver
        self.wait = webdriverwait
        self.cfg = cfg

    def scrape(self, url):

        self.driver.get(url)
        # should check for errors like 404

        # click on the 'View Comments' button to expose comments
        '''check for presence of 'These comments are now closed.'
        If it is there we can keep on pressing the 'More comments' button.
        Otherwise we will see the 'Check for new replies button'
        which can be pressed infintely'''
        # alternative is 'Sign in to comment, reply and react'
        self.click_button(self.cfg['bbc_site']['comments_button'])

        # Repeatedly click on the 'More comments' button until it disappears
        click_again = True
        while click_again:
            click_again = self.click_button(self.cfg['bbc_site']['more_comments_button'])

        # Repeatedly click on the 'More replies' buttons
        more_replies_buttons = self.driver.find_elements(By.XPATH,
                                                         self.cfg['bbc_site']['more_replies_button'])
        for button in more_replies_buttons:
            while True:
                try:
                    ActionChains(self.driver).click(button).perform()
                except WebDriverException:
                    break
        # We've now exposed all the html elements we need to scrape
        # grab the full html
        bs = BeautifulSoup(self.driver.page_source, 'html.parser')
        # BeautifulSoup can't handle xpaths, so we have to class names instead
        contents = bs.find_all('div', class_=self.cfg['bbc_site']['comment_contents'])

        all_data = [[content.findChild('div', selector).text for selector in self.cfg['data_selectors']]
                    for content in contents]

        # place the scraped data into a DataFrame
        df = pd.DataFrame(all_data, columns=self.cfg['df_columns'])
        self.driver.quit()  # close the webdriver

        return df

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


def get_bbc_comments(run_args):
    config = load_config_yaml(run_args.config)

    driver_args = config['ChromeOptions']
    webdriverwait_args = config['WebDriverWait'].values()
    url = config['target_url']
    config_site = config['site']

    driver = setup_driver(*driver_args)
    webdriverwait = WebDriverWait(driver, *webdriverwait_args)

    df = BbcComments(driver, webdriverwait, config_site).scrape(url)
    df.to_csv(args.output, index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Configuration file", required=True)
    parser.add_argument("-o", "--output", help="Output file", required=True)
    args = parser.parse_args()

    get_bbc_comments(args)
