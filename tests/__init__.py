# Fichier __init__.py pour le package tests
"""
Tests Package
=============

Package contenant tous les tests unitaires pour le Stack Overflow Scraper.

Structure des tests:
    - test_scraper.py: Tests pour le module de scraping
    - test_database.py: Tests pour le module de base de données
    - test_analyzer.py: Tests pour le module d'analyse
    - test_config.py: Tests pour le module de configuration

Utilisation:
    pytest tests/
    pytest tests/test_scraper.py
    pytest tests/ -v  # mode verbose
    pytest tests/ -k "test_name"  # exécuter des tests spécifiques
    pytest tests/ --cov=src  # avec couverture de code
"""

__version__ = "1.0.0"
