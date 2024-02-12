from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchDriverException
import os


def setup_driver(*args):
    """Setup chrome webdriver.

    There seems to have been a bug in selenium-manager when installed
    in conda environments
    (see https://github.com/SeleniumHQ/selenium/pull/12536)
    which was fixed but for some reason version in 4.17 it doesn't work properly.
    In order to get around this issue, we need to provide the location of the
    selenium-manager executable. We do this by trying to set the
    environment variable SE_MANAGER_PATH.
    :param args: list
    :return selenium.webdriver
    """
    options = ChromeOptions()
    if not args:
        for arg in args:
            options.add_argument(arg)

    try:
        driver = Chrome(service=Service(), options=options)
    except NoSuchDriverException:
        try:
            # this assumes we are running on a Mac
            os.environ["SE_MANAGER_PATH"] = os.path.join(os.environ["CONDA_PREFIX"],
                                                         "bin", "selenium-manager")
            driver = Chrome(service=Service(), options=options)
        except KeyError:
            print('Could not find the selenium-manager. Quitting.')
            raise SystemExit()

    return driver
