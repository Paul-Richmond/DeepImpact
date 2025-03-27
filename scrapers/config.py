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
    """Configuration for a single selector with various possible types"""
    selector_type: str  # 'label', 'role', 'text', 'test_id', 'id', 'iframe'
    value: Union[str, Pattern]  # Can be either string or compiled regex pattern
    role_name: Optional[Union[str, Pattern]] = None  # Used when selector_type is 'role'
    select_option: Optional[str] = None


@dataclass
class SiteConfig:
    """Configuration for each news site's comment section"""
    # site_code: str
    switch_to_frame_selector: Optional[SelectorConfig] = None
    accept_cookies_selector: Optional[SelectorConfig] = None
    comments_order_selectors: Optional[List[SelectorConfig]] = None
    expose_initial_comments_selector: Optional[SelectorConfig] = None
    page_buttons_selector: Optional[SelectorConfig] = None
    more_comments_selectors: Optional[List[SelectorConfig]] = None
    comments_container_selector: SelectorConfig = None

    def get_container_html(self, page) -> str:
        """Get the HTML content of the comments container"""
        try:
            match self.comments_container_selector.selector_type:
                case 'test_id':
                    return page.get_by_test_id(self.comments_container_selector.value).inner_html()
                case 'label':
                    return page.get_by_label(self.comments_container_selector.value).inner_html()
                case 'id':
                    return page.locator(self.comments_container_selector.value).inner_html()
                case _:
                    raise ValueError(f"Unsupported selector type: {self.comments_container_selector.selector_type}")
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout while getting container HTML: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting container HTML: {e}")
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
