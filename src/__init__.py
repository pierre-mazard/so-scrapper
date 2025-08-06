# Fichier __init__.py pour le package src
"""
Stack Overflow Scraper Package
==============================

Package principal pour l'extraction et l'analyse des données Stack Overflow.

Modules:
    - scraper: Extraction des données via scraping et API
    - database: Gestion de la base de données MongoDB
    - analyzer: Analyse des données et identification des tendances
    - config: Configuration du projet

Classes principales:
    - StackOverflowScraper: Scraper principal
    - DatabaseManager: Gestionnaire de base de données
    - DataAnalyzer: Analyseur de données
    - Config: Configuration
"""

from .scraper import StackOverflowScraper, QuestionData
from .database import DatabaseManager
from .analyzer import DataAnalyzer, NLPProcessor, TrendAnalyzer
from .config import Config, ScraperConfig, DatabaseConfig, APIConfig

__version__ = "1.0.0"
__author__ = "Pierre Mazard"

__all__ = [
    "StackOverflowScraper",
    "QuestionData", 
    "DatabaseManager",
    "DataAnalyzer",
    "NLPProcessor",
    "TrendAnalyzer",
    "Config",
    "ScraperConfig",
    "DatabaseConfig", 
    "APIConfig"
]
