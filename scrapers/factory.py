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

    The ScraperFactory serves as a centralized manager for creating scrapers for various
    websites. By using a dictionary to map site types to their respective scraper classes, 
    the factory allows for dynamic creation of scrapers and easy integration of new scrapers.
    This design promotes maintainability and scalability.

    Attributes:
        _scrapers (Dict[str, Type[BaseScraper]]): A class-level dictionary mapping site 
        types (e.g., 'The Guardian') to their corresponding scraper implementations.
    """

    _scrapers: Dict[str, Type[BaseScraper]] = {
        'The Guardian': GuardianScraper,
        'Daily Mail': DefaultScraper,
        'BBC': DefaultScraper,
        # Add more scrapers here as they are implemented
    }
    """
    Class-level dictionary storing mappings of site types to their scraper classes.
    
    This dictionary acts as a registry for all supported site types and their scraper
    implementations. Developers can extend functionality by adding new entries to
    this registry or by using the `register_scraper` method.
    """

    @classmethod
    def create_scraper(cls, site_type: str, config: SiteConfig) -> BaseScraper:
        """
        Create and return a scraper for the specified site type

        Args:
            site_type: Type of website (e.g., 'The Guardian', 'BBC', 'Daily Mail')
            config: Site configuration

        Returns:
            BaseScraper: An instance of the appropriate scraper

        Raises:
            ValueError: If the site type is not supported
        """
        if site_type not in cls._scrapers:
            logger.warning(f"Unknown site type '{site_type}'. Using default scraper.")
            return DefaultScraper(config)

        return cls._scrapers[site_type](config)

    @classmethod
    def register_scraper(cls, site_type: str, scraper_class: Type[BaseScraper]) -> None:
        """
        Register a new scraper class for a specific site type.
    
        This method allows the dynamic addition of a scraper class to the factory's
        internal registry. It is useful for extending the factory's functionality
        by supporting additional site types without modifying the core code.
    
        Args:
            site_type (str): The name of the site (e.g., 'New York Times').
            scraper_class (Type[BaseScraper]): The scraper class to associate with the site type.
    
        Returns:
            None
        """
        cls._scrapers[site_type] = scraper_class
