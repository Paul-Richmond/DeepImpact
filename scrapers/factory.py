import logging
from typing import Dict, Type

from .base import BaseScraper
from .config import SiteConfig
from .sites.default import DefaultScraper
from .sites.guardian import GuardianScraper

logger = logging.getLogger(__name__)


class ScraperFactory:
    """Factory class to create appropriate scrapers based on website"""

    _scrapers: Dict[str, Type[BaseScraper]] = {
        'The Guardian': GuardianScraper,
        'Daily Mail': DefaultScraper,
        'BBC': DefaultScraper,
        # Add more scrapers here as they are implemented
    }

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
        """Register a new scraper class for a site type"""
        cls._scrapers[site_type] = scraper_class
