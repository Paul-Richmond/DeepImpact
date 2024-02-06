import argparse
import configparser
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import pandas as pd
from utils.helpers import setup_driver


class BbcComments:
    def __init__(self, driver, cfg):
        self.driver = driver
        self.cfg = cfg
        self.wait = self.get_wait()

    def scrape(self, url):

        self.driver.get(url)
        # should check for errors like 404

        # click on the 'View Comments' button to expose comments
        '''check for presence of 'These comments are now closed.'
        If it is there we can keep on pressing the 'More comments' button.
        Otherwise we will see the 'Check for new replies button'
        which can be pressed infintely'''
        # alternative is 'Sign in to comment, reply and react'
        self.click_button(self.cfg['BBC_SITE']['comments_button'])

        # Repeatedly click on the 'More comments' button until it disappears
        click_again = True
        while click_again:
            click_again = self.click_button(self.cfg['BBC_SITE']['more_comments_button'])

        # Repeatedly click on the 'More replies' buttons
        more_replies_buttons = self.driver.find_elements(By.XPATH,
                                                         self.cfg['BBC_SITE']['more_replies_button'])
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
        contents = bs.find_all('div', class_=self.cfg['BBC_SITE']['comment_contents'])

        data = [value for value in self.cfg['DATA'].values()]
        all_data = [[content.findChild('div', eval(datum)).text for datum in data]
                    for content in contents]

        # place the scraped data into a DataFrame
        df = pd.DataFrame(all_data, columns=['Comment', 'Post Date', 'Likes', 'Dislikes'])
        self.driver.quit()  # close the webdriver

        return df

    def get_wait(self):
        try:
            wait_time = float(self.cfg['BBC_SITE']['wait_time'])
        except ValueError:
            wait_time = 2  # set a default value

        return WebDriverWait(self.driver, wait_time)

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
    config = configparser.ConfigParser()
    config.read(run_args.config)

    driver = setup_driver(config)

    df = BbcComments(driver, config).scrape(config['BBC_SITE']['target_url'])
    df.to_csv(args.output, index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Configuration file", required=True)
    parser.add_argument("-o", "--output", help="Output file", required=True)
    args = parser.parse_args()

    get_bbc_comments(args)
