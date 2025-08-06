"""
Tests pour le module Config
===========================

Tests unitaires pour vérifier le bon fonctionnement de la configuration.
"""

import pytest
import os
import json
import tempfile
from unittest.mock import patch, mock_open

from src.config import Config, ScraperConfig, DatabaseConfig, APIConfig


class TestScraperConfig:
    """Tests pour la classe ScraperConfig."""
    
    def test_scraper_config_defaults(self):
        """Test les valeurs par défaut de ScraperConfig."""
        config = ScraperConfig()
        
        assert config.headless is True
        assert config.retry_count == 3
        assert config.delay_between_requests == 2.0
        assert config.timeout == 30
        assert config.max_pages == 5
        assert "Mozilla" in config.user_agent
    
    def test_scraper_config_custom(self):
        """Test ScraperConfig avec valeurs personnalisées."""
        config = ScraperConfig(
            headless=False,
            retry_count=5,
            delay_between_requests=1.0,
            timeout=60,
            max_pages=10,
            base_url="https://custom.com"
        )
        
        assert config.headless is False
        assert config.retry_count == 5
        assert config.delay_between_requests == 1.0
        assert config.timeout == 60
        assert config.max_pages == 10
        assert config.base_url == "https://custom.com"


class TestDatabaseConfig:
    """Tests pour la classe DatabaseConfig."""
    
    def test_database_config_defaults(self):
        """Test les valeurs par défaut de DatabaseConfig."""
        config = DatabaseConfig()
        
        assert config.host == "localhost"
        assert config.port == 27017
        assert config.name == "stackoverflow_data"
        assert config.collection == "questions"
        assert config.max_pool_size == 10
        assert config.timeout_ms == 30000
    
    def test_database_config_custom(self):
        """Test DatabaseConfig avec valeurs personnalisées."""
        config = DatabaseConfig(
            host="custom",
            port=27018,
            name="custom_db",
            collection="custom_questions"
        )
        
        assert config.host == "custom"
        assert config.port == 27018
        assert config.name == "custom_db"
        assert config.collection == "custom_questions"


class TestAPIConfig:
    """Tests pour la classe APIConfig."""
    
    def test_api_config_defaults(self):
        """Test les valeurs par défaut de APIConfig."""
        config = APIConfig()
        
        assert config.key == ""
        assert config.rate_limit == 300
        assert config.quota_max == 10000
        assert config.site == "stackoverflow"
    
    def test_api_config_custom(self):
        """Test APIConfig avec valeurs personnalisées."""
        config = APIConfig(
            key="test_key",
            rate_limit=500,
            quota_max=20000,
            site="meta.stackoverflow"
        )
        
        assert config.key == "test_key"
        assert config.rate_limit == 500
        assert config.quota_max == 20000
        assert config.site == "meta.stackoverflow"


class TestConfig:
    """Tests pour la classe Config principale."""
    
    def test_config_initialization_default(self):
        """Test l'initialisation avec configuration par défaut."""
        config = Config()
        
        assert isinstance(config.scraper_config, ScraperConfig)
        assert isinstance(config.database_config, DatabaseConfig)
        assert isinstance(config.api_config, APIConfig)
    
    def test_config_with_file(self):
        """Test l'initialisation avec fichier de configuration."""
        config_data = {
            "scraper": {
                "headless": False,
                "retry_count": 5,
                "timeout": 45
            },
            "database": {
                "name": "test_db",
                "host": "test",
                "port": 27017
            },
            "api": {
                "key": "test_api_key",
                "rate_limit": 400
            }
        }
        
        config_json = json.dumps(config_data)
        
        with patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=config_json)):
            
            config = Config("test_config.json")
            
            assert config.scraper_config.headless is False
            assert config.scraper_config.retry_count == 5
            assert config.scraper_config.timeout == 45
            assert config.database_config.name == "test_db"
            assert config.api_config.key == "test_api_key"
            assert config.api_config.rate_limit == 400
    
    def test_config_file_not_exists(self):
        """Test l'initialisation quand le fichier de configuration n'existe pas."""
        with patch("os.path.exists", return_value=False):
            config = Config("nonexistent_config.json")
            
            # Doit utiliser les valeurs par défaut
            assert config.scraper_config.headless is True
            assert config.database_config.name == "stackoverflow_data"
    
    def test_config_invalid_json_file(self):
        """Test l'initialisation avec fichier JSON invalide."""
        invalid_json = "{ invalid json"
        
        with patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=invalid_json)), \
             patch("builtins.print") as mock_print:
            
            config = Config("invalid_config.json")
            
            # Doit utiliser les valeurs par défaut et afficher une erreur
            assert config.scraper_config.headless is True
            mock_print.assert_called_once()
            assert "Erreur lors du chargement" in mock_print.call_args[0][0]
    
    @patch.dict(os.environ, {
        "SO_SCRAPER_USER_AGENT": "Custom User Agent",
        "SO_SCRAPER_HEADLESS": "false",
        "SO_SCRAPER_RETRY_COUNT": "7",
        "MONGODB_HOST": "env",
        "MONGODB_PORT": "27018",
        "MONGODB_DATABASE_NAME": "env_db",
        "STACKOVERFLOW_API_KEY": "env_api_key"
    })
    def test_config_from_environment(self):
        """Test la configuration depuis les variables d'environnement."""
        config = Config()
        
        assert config.scraper_config.user_agent == "Custom User Agent"
        assert config.scraper_config.headless is False
        assert config.scraper_config.retry_count == 7
        assert config.database_config.host == "env"
        assert config.database_config.port == 27018
        assert config.database_config.name == "env_db"
        assert config.api_config.key == "env_api_key"
    
    @patch.dict(os.environ, {"SO_SCRAPER_HEADLESS": "true"})
    def test_config_environment_boolean_true(self):
        """Test la conversion boolean true depuis l'environnement."""
        config = Config()
        assert config.scraper_config.headless is True
    
    @patch.dict(os.environ, {"SO_SCRAPER_HEADLESS": "True"})
    def test_config_environment_boolean_true_case(self):
        """Test la conversion boolean true avec différente casse."""
        config = Config()
        assert config.scraper_config.headless is True
    
    @patch.dict(os.environ, {"SO_SCRAPER_HEADLESS": "anything_else"})
    def test_config_environment_boolean_false(self):
        """Test la conversion boolean false depuis l'environnement."""
        config = Config()
        assert config.scraper_config.headless is False
    
    def test_save_config(self):
        """Test la sauvegarde de configuration."""
        config = Config()
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
            temp_filename = temp_file.name
        
        try:
            config.save_config(temp_filename)
            
            # Vérifier que le fichier a été créé et contient la configuration
            assert os.path.exists(temp_filename)
            
            with open(temp_filename, 'r', encoding='utf-8') as f:
                saved_config = json.load(f)
            
            assert "scraper" in saved_config
            assert "database" in saved_config
            assert "api" in saved_config
            assert saved_config["scraper"]["headless"] == config.scraper_config.headless
            assert saved_config["database"]["name"] == config.database_config.name
        
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
    
    def test_save_config_error(self):
        """Test la sauvegarde avec erreur d'écriture."""
        config = Config()
        
        with patch("builtins.open", side_effect=PermissionError("Permission denied")), \
             patch("builtins.print") as mock_print:
            
            config.save_config("/invalid/path/config.json")
            
            mock_print.assert_called_once()
            assert "Erreur lors de la sauvegarde" in mock_print.call_args[0][0]
    
    def test_get_chrome_options(self):
        """Test la récupération des options Chrome."""
        config = Config()
        chrome_options = config.get_chrome_options()
        
        assert "headless" in chrome_options
        assert "user_agent" in chrome_options
        assert "timeout" in chrome_options
        assert chrome_options["headless"] == config.scraper_config.headless
        assert chrome_options["user_agent"] == config.scraper_config.user_agent
        assert chrome_options["timeout"] == config.scraper_config.timeout
    
    def test_get_mongodb_url(self):
        """Test la récupération de l'URL MongoDB."""
        config = Config()
        url = config.get_mongodb_url()
        
        assert url == f"mongodb://{config.database_config.host}:{config.database_config.port}/"
    
    def test_config_str_representation(self):
        """Test la représentation string de la configuration."""
        config = Config()
        config_str = str(config)
        
        assert "Stack Overflow Scraper Configuration" in config_str
        assert "Scraper:" in config_str
        assert "Database:" in config_str
        assert "API:" in config_str
        assert str(config.scraper_config.headless) in config_str
        assert config.database_config.name in config_str
    
    def test_config_priority_environment_over_file(self):
        """Test que les variables d'environnement ont priorité sur le fichier."""
        config_data = {
            "scraper": {
                "headless": True,
                "retry_count": 3
            }
        }
        config_json = json.dumps(config_data)
        
        with patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=config_json)), \
             patch.dict(os.environ, {"SO_SCRAPER_HEADLESS": "false", "SO_SCRAPER_RETRY_COUNT": "5"}):
            
            config = Config("test_config.json")
            
            # Les variables d'environnement doivent prendre le dessus
            assert config.scraper_config.headless is False
            assert config.scraper_config.retry_count == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
