"""
ScraperFactory module.

This module provides the ScraperFactory class, a centralized component for managing 
and creating scraper instances for different types of websites. It is designed 
to facilitate the dynamic creation of website scrapers and improve maintainability 
by allowing new types of scrapers to be easily registered and used.

Classes:
    - ScraperFactory: Factory class for creating and managing website scrapers.
"""

import logging
from typing import Dict, Type

from .base import BaseScraper
from .config import SiteConfig
from .sites.default import DefaultScraper
from .sites.guardian import GuardianScraper

logger = logging.getLogger(__name__)


class ScraperFactory:
    """
    Factory class for managing and creating scraper instances for different website types.

    The ScraperFactory serves as a centralized manager for creating and configuring scrapers
    for various websites. It uses dictionaries to map site types to their respective scraper
    classes and configuration files, allowing for dynamic instantiation of scrapers based on
    site-specific requirements.

    This design pattern promotes:
    - Encapsulation: Hiding the complexity of scraper creation
    - Extensibility: Easy integration of new scrapers without modifying client code
    - Maintainability: Centralized management of scraper configurations
    - Flexibility: Runtime registration of new scrapers and configurations

    Attributes:
        _scrapers (Dict[str, Type[BaseScraper]]): Maps site types to their corresponding
                                                  scraper implementations.
        _site_configs (Dict[str, str]): Maps site types to their respective configuration
                                        file paths.
    """

    _scrapers: Dict[str, Type[BaseScraper]] = {
        "The Guardian": GuardianScraper,
        "Daily Mail": DefaultScraper,
        "BBC": DefaultScraper,
        # Add more scrapers here as they are implemented
    }
    """
    Class-level dictionary mapping site types to their respective scraper classes.

    Each key is a string identifying a website (e.g., 'The Guardian'), and each value
    is a class (not an instance) that inherits from BaseScraper. The factory uses this
    registry to instantiate the appropriate scraper when create_scraper is called.

    This dictionary is populated with built-in scrapers by default and can be extended
    at runtime using the register_scraper method.
    """

    _site_configs: Dict[str, str] = {
        "The Guardian": "./configs/guardian.yaml",
        "Daily Mail": "./configs/dailymail.yaml",
        "BBC": "./configs/bbc.yaml"
        # Add more site configurations here as they are implemented
    }
    """
    Class-level dictionary mapping site types to their configuration file paths.

    Each key is a string identifying a website (e.g., 'The Guardian'), and each value
    is a string representing the path to a YAML configuration file.

    This registry complements the _scrapers dictionary by providing site-specific
    configurations needed to properly initialize each scraper.
    """

    @classmethod
    def create_scraper(cls, site_type: str, config: SiteConfig) -> BaseScraper:
        """
        Create and return a scraper instance for the specified site type.

        This method instantiates the appropriate scraper class based on the provided site type.
        If the site type is not registered, it falls back to the DefaultScraper.

        Args:
            site_type (str): Type of website (e.g., 'The Guardian', 'BBC', 'Daily Mail')
            config (SiteConfig): Configuration settings for the scraper

        Returns:
            BaseScraper: An initialized scraper instance configured for the specified site

        Raises:
            ValueError: If the site type is not supported and no default scraper is available
        """

        if site_type not in cls._scrapers:
            logger.warning(f"Unknown site type '{site_type}'. Using default scraper.")
            return DefaultScraper(config)

        return cls._scrapers[site_type](config)

    @classmethod
    def register_scraper(cls, site_type: str, scraper_class: Type[BaseScraper]) -> None:
        """
        Register a new scraper class for a specific site type.

        This method enables runtime extension of supported site types by adding new
        entries to the scraper registry.

        Args:
            site_type (str): Type of website (e.g., 'The Guardian', 'BBC', 'Daily Mail')
            scraper_class (Type[BaseScraper]): The scraper class to associate with the site type
                Must be a subclass of BaseScraper

        Returns:
            None
        """

        cls._scrapers[site_type] = scraper_class

    @classmethod
    def get_config_path(cls, site_type: str) -> str:
        """
        Retrieve the configuration file path for a specific site type.

        This method looks up the registered configuration file path for the given
        site type from the _site_configs dictionary.

        Args:
            site_type (str): Type of website (e.g., 'The Guardian', 'BBC', 'Daily Mail')

        Returns:
            str: Absolute or relative path to the configuration file

        Raises:
            ValueError: If the site type does not have a registered configuration path
        """

        if site_type not in cls._site_configs:
            raise ValueError(f"No configuration registered for site type: {site_type}")

        return cls._site_configs[site_type]

    @classmethod
    def register_site_config(cls, site_type: str, config_path: str) -> None:
        """
        Register a configuration file path for a specific site type.

        This method associates a site type with its configuration file path, allowing
        the factory to locate site-specific settings when creating scrapers.

        Args:
            site_type (str): Type of website (e.g., 'The Guardian', 'BBC', 'Daily Mail')
            config_path (str): Path to the YAML configuration file containing scraper settings

        Returns:
            None
        """

        cls._site_configs[site_type] = config_path
