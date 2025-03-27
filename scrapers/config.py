"""
Configuration Module for the News Scraper.

This module is designed to handle all aspects of configuration management required for the news scraper. 
It provides classes and utility functions to define, validate, and manage configurations that control the scraper's behavior.

Capabilities include:
1. Defining and storing selectors for targeting specific website elements (e.g., cookie buttons, comment sections).
2. Loading configuration data from YAML files and converting them into Python data models.
3. Validating the structure and completeness of the configuration data.
4. Supporting regex-based and Playwright-compatible selectors for dynamic web scraping needs.
5. Handling configuration formats that improve compatibility and maintainability.

Components:
- SelectorConfig: A data model for specifying individual web element selectors, including Playwright-specific types.
- SiteConfig: A data model for organizing all selectors associated with a specific website.
- Utility Functions: Tools for loading configurations from YAML and converting them into Python objects.

This module ensures the scraper operates efficiently with well-defined configurations tailored to various website structures.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Pattern, Union

import yaml
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)


#############
# Data Models
#############

@dataclass
class SelectorConfig:
    """
    Configuration for a single selector used to identify elements on a webpage.

    Attributes:
       selector_type: Type of selector, most match Playwright locator.get_by_# method (e.g., 'role' for get_by_role)
       value: The selector value/expression
       role_name: Name attribute when using role selectors
       select_option: Option value for selection elements
    """

    selector_type: str  # 'iframe', 'role', 'label', 'placeholder', 'text', 'alt_text', 'title', 'test_id', 'id'
    value: Union[str, Pattern]  # Can be either string or compiled regex pattern
    role_name: Optional[Union[str, Pattern]] = None  # Used when selector_type is 'role'
    select_option: Optional[str] = None


@dataclass
class SiteConfig:
    """
       Configuration for website selectors used during scraping.

       Attributes:
           switch_to_frame_selector: Selector for iframes containing elements (e.g., cookie dialogs)
           accept_cookies_selector: Selector for cookie consent button
           comments_order_selectors: Selectors for comment ordering options
           expose_initial_comments_selector: Selector to expand initial comments
           page_buttons_selector: Selector for pagination buttons
           more_comments_selectors: Selectors for buttons that expose more comments or text (e.g., "Show more")
           comments_container_selector: Selector for the container which holds all comments and other data e.g., usernames, likes, etc.
       """

    switch_to_frame_selector: Optional[SelectorConfig] = None
    accept_cookies_selector: Optional[SelectorConfig] = None
    comments_order_selectors: Optional[List[SelectorConfig]] = None
    expose_initial_comments_selector: Optional[SelectorConfig] = None
    page_buttons_selector: Optional[SelectorConfig] = None
    more_comments_selectors: Optional[List[SelectorConfig]] = None
    comments_container_selector: SelectorConfig = None

    def get_container_html(self, page) -> str:
        """
        Get the HTML content of the comments container

        Args:
            page: The page object to get content from

        Returns:
            str: HTML content of the container

        Raises:
            PlaywrightTimeoutError: If the container cannot be found within timeout
            ValueError: If there's an invalid selector configuration
            Exception: For other unexpected errors
        """
        try:
            # Use a delayed/local import to break the circular dependency
            from .utils import get_locator

            container = get_locator(page, self.comments_container_selector)
            return container.inner_html()
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout while getting container HTML: {e}")
            raise
        except ValueError as e:
            logger.error(f"Invalid selector configuration: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while getting container HTML: {str(e)}")
            raise


###########################
# Configuration Utilities
###########################

def convert_selector_config(selector_dict: Dict[str, Any]) -> SelectorConfig:
    """
    Convert a dictionary to a SelectorConfig object

    Args:
        selector_dict: Dictionary containing selector configuration

    Returns:
        SelectorConfig object

    Raises:
        ValueError: If an unknown key is found in selector_dict
    """
    if 'iframe' in selector_dict:
        return SelectorConfig(
            selector_type='iframe',
            value=selector_dict['iframe']
        )
    elif 'role' in selector_dict:
        return SelectorConfig(
            selector_type='role',
            value=selector_dict['role'],
            role_name=selector_dict.get('name')
        )
    elif 'label' in selector_dict:
        return SelectorConfig(
            selector_type='label',
            value=selector_dict['label']
        )
    elif 'placeholder' in selector_dict:
        return SelectorConfig(
            selector_type='placeholder',
            value=selector_dict['placeholder']
        )
    elif 'text' in selector_dict:
        return SelectorConfig(
            selector_type='text',
            value=selector_dict['text']
        )
    elif 'alt_text' in selector_dict:
        return SelectorConfig(
            selector_type='alt_text',
            value=selector_dict['alt_text']
        )
    elif 'title' in selector_dict:
        return SelectorConfig(
            selector_type='title',
            value=selector_dict['title']
        )
    elif 'test_id' in selector_dict:
        return SelectorConfig(
            selector_type='test_id',
            value=selector_dict['test_id'],
            select_option=selector_dict.get('select_option')
        )
    elif 'id' in selector_dict:
        return SelectorConfig(
            selector_type='id',
            value=selector_dict['id']
        )
    else:
        raise ValueError(f"Unknown selector type in configuration: {selector_dict}")


def load_site_config(yaml_path: str, config_name: str) -> SiteConfig:
    """
    Load YAML file and convert to SiteConfig object for specified configuration

    Args:
        yaml_path: Path to YAML configuration file
        config_name: Name of the configuration to load (e.g., 'dm_cfg1')

    Returns:
        SiteConfig object for the specified configuration

    Raises:
        ValueError: If the specified configuration name is not found in the YAML file
    """
    # Add a constructor to yaml.Loader which will convert the YAML tag
    # !!python/object/apply:re._compile
    # into a re.compile object
    yaml.Loader.add_constructor('!!python/object/apply:re._compile',
                                lambda loader, node: re.compile(*loader.construct_sequence(node)))
    with open(yaml_path, 'r') as file:
        yaml_config = yaml.load(file, Loader=yaml.Loader)

    if config_name not in yaml_config:
        raise ValueError(f"Configuration '{config_name}' not found in YAML file")

    config = yaml_config[config_name]

    # Convert each selector configuration
    # each key of `site_config_dict` should match a SiteConfig attribute
    site_config_dict = {
        'switch_to_frame_selector': (
            convert_selector_config(config['switch_to_frame_selector'])
            if 'switch_to_frame_selector' in config else None
        ),
        'accept_cookies_selector': (
            convert_selector_config(config['accept_cookies_selector'])
            if 'accept_cookies_selector' in config else None
        ),
        'comments_order_selectors': (
            [convert_selector_config(selector) for selector in config['comments_order_selectors']]
            if 'comments_order_selectors' in config else None
        ),
        'expose_initial_comments_selector': (
            convert_selector_config(config['expose_initial_comments_selector'])
            if 'expose_initial_comments_selector' in config else None
        ),
        'page_buttons_selector': (
            convert_selector_config(config['page_buttons_selector'])
            if 'page_buttons_selector' in config else None
        ),
        'more_comments_selectors': (
            [convert_selector_config(selector) for selector in config['more_comments_selectors']]
            if 'more_comments_selectors' in config else None
        ),
        'comments_container_selector': (
            convert_selector_config(config['comments_container_selector'])
            if 'comments_container_selector' in config else None
        )
    }

    return SiteConfig(**site_config_dict)
