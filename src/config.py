"""
Configuration Module
===================

Module de configuration pour le Stack Overflow Scraper.
Centralise tous les paramètres de configuration du projet.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
import json


@dataclass
class ScraperConfig:
    """Configuration pour le scraper."""
    base_url: str = "https://stackoverflow.com"
    max_pages: int = 5
    delay_between_requests: float = 2.0
    headless: bool = True
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    timeout: int = 30
    retry_count: int = 3


@dataclass
class DatabaseConfig:
    """Configuration pour la base de données."""
    host: str = "localhost"
    port: int = 27017
    name: str = "stackoverflow_data"
    collection: str = "questions"
    max_pool_size: int = 10
    timeout_ms: int = 30000


@dataclass
class APIConfig:
    """Configuration pour l'API Stack Overflow."""
    key: str = ""
    rate_limit: int = 300
    quota_max: int = 10000
    site: str = "stackoverflow"


class Config:
    """
    Classe principale de configuration.
    
    Charge la configuration depuis les variables d'environnement et/ou
    un fichier de configuration.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialise la configuration.
        
        Args:
            config_file: Chemin vers le fichier de configuration JSON (optionnel)
        """
        self.config_file = config_file or "config.json"
        self._load_config()
    
    def _load_config(self):
        """Charge la configuration depuis les sources disponibles."""
        # Configuration par défaut qui correspond au schema de config.json
        default_config = {
            "scraper": {
                "base_url": "https://stackoverflow.com",
                "max_pages": 5,
                "delay_between_requests": 2,
                "headless": True,
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "timeout": 30,
                "retry_count": 3
            },
            "database": {
                "host": "localhost",
                "port": 27017,
                "name": "stackoverflow_data",
                "collection": "questions",
                "max_pool_size": 10,
                "timeout_ms": 30000
            },
            "api": {
                "key": "",
                "rate_limit": 300,
                "quota_max": 10000,
                "site": "stackoverflow"
            }
        }
        
        # Charger depuis le fichier de configuration s'il existe
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    default_config.update(file_config)
            except Exception as e:
                print(f"Erreur lors du chargement du fichier de config: {e}")
        
        # Surcharger avec les variables d'environnement
        self._load_from_environment(default_config)
        
        # Créer les objets de configuration
        self.scraper_config = ScraperConfig(**default_config["scraper"])
        self.database_config = DatabaseConfig(**default_config["database"])
        self.api_config = APIConfig(**default_config["api"])
    
    def _load_from_environment(self, config: Dict[str, Any]):
        """Charge les paramètres depuis les variables d'environnement."""
        # Configuration du scraper
        if os.getenv("SO_SCRAPER_USER_AGENT"):
            config["scraper"]["user_agent"] = os.getenv("SO_SCRAPER_USER_AGENT")
        
        if os.getenv("SO_SCRAPER_HEADLESS"):
            config["scraper"]["headless"] = os.getenv("SO_SCRAPER_HEADLESS").lower() == "true"
        
        if os.getenv("SO_SCRAPER_RETRY_COUNT"):
            config["scraper"]["retry_count"] = int(os.getenv("SO_SCRAPER_RETRY_COUNT"))
        
        # Configuration de la base de données
        if os.getenv("MONGODB_HOST"):
            config["database"]["host"] = os.getenv("MONGODB_HOST")
        
        if os.getenv("MONGODB_PORT"):
            config["database"]["port"] = int(os.getenv("MONGODB_PORT"))
        
        if os.getenv("MONGODB_DATABASE_NAME"):
            config["database"]["name"] = os.getenv("MONGODB_DATABASE_NAME")
        
        # Configuration de l'API
        if os.getenv("STACKOVERFLOW_API_KEY"):
            config["api"]["key"] = os.getenv("STACKOVERFLOW_API_KEY")
    
    def save_config(self, filename: Optional[str] = None):
        """
        Sauvegarde la configuration actuelle dans un fichier.
        
        Args:
            filename: Nom du fichier de sauvegarde (optionnel)
        """
        filename = filename or self.config_file
        
        config_dict = {
            "scraper": {
                "base_url": self.scraper_config.base_url,
                "max_pages": self.scraper_config.max_pages,
                "delay_between_requests": self.scraper_config.delay_between_requests,
                "headless": self.scraper_config.headless,
                "user_agent": self.scraper_config.user_agent,
                "timeout": self.scraper_config.timeout,
                "retry_count": self.scraper_config.retry_count
            },
            "database": {
                "host": self.database_config.host,
                "port": self.database_config.port,
                "name": self.database_config.name,
                "collection": self.database_config.collection,
                "max_pool_size": self.database_config.max_pool_size,
                "timeout_ms": self.database_config.timeout_ms
            },
            "api": {
                "key": self.api_config.key,
                "rate_limit": self.api_config.rate_limit,
                "quota_max": self.api_config.quota_max,
                "site": self.api_config.site
            }
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            print(f"Configuration sauvegardée dans {filename}")
        except Exception as e:
            print(f"Erreur lors de la sauvegarde de la configuration: {e}")
    
    def get_chrome_options(self) -> Dict[str, Any]:
        """Retourne les options Chrome pour Selenium."""
        return {
            "headless": self.scraper_config.headless,
            "user_agent": self.scraper_config.user_agent,
            "timeout": self.scraper_config.timeout
        }
    
    def get_mongodb_url(self) -> str:
        """Retourne l'URL complète de MongoDB."""
        return f"mongodb://{self.database_config.host}:{self.database_config.port}/"
    
    def __str__(self) -> str:
        """Représentation string de la configuration."""
        return f"""Stack Overflow Scraper Configuration:
        
Scraper:
  - Base URL: {self.scraper_config.base_url}
  - User Agent: {self.scraper_config.user_agent[:50]}...
  - Headless: {self.scraper_config.headless}
  - Max Pages: {self.scraper_config.max_pages}
  - Retry Count: {self.scraper_config.retry_count}
  - Delay: {self.scraper_config.delay_between_requests}s
  - Timeout: {self.scraper_config.timeout}s

Database:
  - Host: {self.database_config.host}
  - Port: {self.database_config.port}
  - Database: {self.database_config.name}
  - Collection: {self.database_config.collection}

API:
  - API Key: {'Set' if self.api_config.key else 'Not set'}
  - Rate Limit: {self.api_config.rate_limit} req/s
  - Quota Max: {self.api_config.quota_max}
  - Site: {self.api_config.site}
"""
