"""
Configuration de logging pour les tests
======================================

Module pour configurer le système de logging spécifiquement pour la suite de tests.
Capture les résultats et les erreurs dans des fichiers de log détaillés.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path


class TestLogger:
    """Gestionnaire de logs pour les tests."""
    
    def __init__(self):
        """Initialise le système de logging pour les tests."""
        self.logs_dir = Path(__file__).parent / "logs"
        self.logs_dir.mkdir(exist_ok=True)
        
        # Timestamp pour les fichiers de log
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Configuration des fichiers de log
        self.log_files = {
            'main': self.logs_dir / f"test_run_{timestamp}.log",
            'errors': self.logs_dir / f"test_errors_{timestamp}.log",
            'summary': self.logs_dir / f"test_summary_{timestamp}.log"
        }
        
        self._setup_loggers()
    
    def _setup_loggers(self):
        """Configure les différents loggers."""
        
        # Logger principal pour tous les tests
        self.main_logger = logging.getLogger('test_main')
        self.main_logger.setLevel(logging.DEBUG)
        
        # Logger pour les erreurs uniquement
        self.error_logger = logging.getLogger('test_errors')
        self.error_logger.setLevel(logging.ERROR)
        
        # Logger pour le résumé
        self.summary_logger = logging.getLogger('test_summary')
        self.summary_logger.setLevel(logging.INFO)
        
        # Formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Handler pour le fichier principal
        main_handler = logging.FileHandler(self.log_files['main'], encoding='utf-8')
        main_handler.setLevel(logging.DEBUG)
        main_handler.setFormatter(detailed_formatter)
        
        # Handler pour les erreurs
        error_handler = logging.FileHandler(self.log_files['errors'], encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        
        # Handler pour le résumé
        summary_handler = logging.FileHandler(self.log_files['summary'], encoding='utf-8')
        summary_handler.setLevel(logging.INFO)
        summary_handler.setFormatter(simple_formatter)
        
        # Ajout des handlers
        self.main_logger.addHandler(main_handler)
        self.error_logger.addHandler(error_handler)
        self.summary_logger.addHandler(summary_handler)
        
        # Éviter la propagation vers le logger racine
        self.main_logger.propagate = False
        self.error_logger.propagate = False
        self.summary_logger.propagate = False
    
    def log_test_start(self, test_name: str, module: str):
        """Log le début d'un test."""
        self.main_logger.info(f"🚀 DÉBUT TEST: {test_name} [{module}]")
        
    def log_test_pass(self, test_name: str, duration: float = None):
        """Log la réussite d'un test."""
        duration_str = f" ({duration:.2f}s)" if duration else ""
        self.main_logger.info(f"✅ RÉUSSI: {test_name}{duration_str}")
        
    def log_test_fail(self, test_name: str, error: str, duration: float = None):
        """Log l'échec d'un test."""
        duration_str = f" ({duration:.2f}s)" if duration else ""
        self.main_logger.error(f"❌ ÉCHEC: {test_name}{duration_str}")
        self.main_logger.error(f"   Erreur: {error}")
        self.error_logger.error(f"ÉCHEC: {test_name} - {error}")
        
    def log_test_error(self, test_name: str, error: str, duration: float = None):
        """Log l'erreur d'un test (différent d'un échec)."""
        duration_str = f" ({duration:.2f}s)" if duration else ""
        self.main_logger.error(f"🚫 ERREUR: {test_name}{duration_str}")
        self.main_logger.error(f"   Erreur: {error}")
        self.error_logger.error(f"ERREUR: {test_name} - {error}")
        
    def log_test_skip(self, test_name: str, reason: str):
        """Log le skip d'un test."""
        self.main_logger.warning(f"⏭️  IGNORÉ: {test_name}")
        self.main_logger.warning(f"   Raison: {reason}")
        
    def log_suite_start(self, suite_name: str):
        """Log le début d'une suite de tests."""
        self.main_logger.info(f"📋 DÉBUT SUITE: {suite_name}")
        self.summary_logger.info(f"=== DÉBUT SUITE: {suite_name} ===")
        
    def log_suite_end(self, suite_name: str, stats: dict):
        """Log la fin d'une suite de tests."""
        self.main_logger.info(f"📊 FIN SUITE: {suite_name}")
        self.summary_logger.info(f"=== FIN SUITE: {suite_name} ===")
        self.summary_logger.info(f"Résultats: {stats['passed']} réussis, {stats['failed']} échecs, {stats['skipped']} ignorés")
        
    def log_session_summary(self, total_stats: dict):
        """Log le résumé complet de la session de tests."""
        self.summary_logger.info("=" * 60)
        self.summary_logger.info("RÉSUMÉ GLOBAL DE LA SESSION DE TESTS")
        self.summary_logger.info("=" * 60)
        self.summary_logger.info(f"✅ Tests réussis: {total_stats['passed']}")
        self.summary_logger.info(f"❌ Tests échoués: {total_stats['failed']}")
        self.summary_logger.info(f"⏭️  Tests ignorés: {total_stats['skipped']}")
        self.summary_logger.info(f"⏱️  Durée totale: {total_stats['duration']:.2f}s")
        
        if total_stats['failed'] == 0:
            self.summary_logger.info("🎉 TOUS LES TESTS ONT RÉUSSI!")
        else:
            self.summary_logger.warning(f"⚠️  {total_stats['failed']} test(s) ont échoué")
            
        self.summary_logger.info("=" * 60)


# Instance globale du logger de test
test_logger = TestLogger()


def setup_test_logging():
    """Configure le logging pour les tests."""
    return test_logger
