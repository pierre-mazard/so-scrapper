"""
Plugin pytest pour le logging des résultats de tests
==================================================

Plugin personnalisé pour capturer et logger automatiquement
tous les événements de test dans des fichiers de log détaillés.
"""

import pytest
import time
from .test_logger import setup_test_logging


class TestResultsPlugin:
    """Plugin pytest pour logger les résultats des tests."""
    
    def __init__(self):
        """Initialise le plugin de logging."""
        self.logger = setup_test_logging()
        self.session_start_time = None
        self.test_start_time = None
        self.stats = {
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'error': 0
        }
        
    def pytest_sessionstart(self, session):
        """Appelé au début de la session pytest."""
        self.session_start_time = time.time()
        self.logger.main_logger.info("=" * 80)
        self.logger.main_logger.info("🔬 DÉBUT DE LA SESSION DE TESTS")
        self.logger.main_logger.info("=" * 80)
        self.logger.summary_logger.info("DÉBUT DE LA SESSION DE TESTS - " + 
                                       time.strftime("%Y-%m-%d %H:%M:%S"))
        
    def pytest_sessionfinish(self, session, exitstatus):
        """Appelé à la fin de la session pytest."""
        duration = time.time() - self.session_start_time if self.session_start_time else 0
        
        total_stats = {
            **self.stats,
            'duration': duration,
            'exit_status': exitstatus
        }
        
        self.logger.log_session_summary(total_stats)
        self.logger.main_logger.info("=" * 80)
        self.logger.main_logger.info("🏁 FIN DE LA SESSION DE TESTS")
        self.logger.main_logger.info(f"   Durée totale: {duration:.2f} secondes")
        self.logger.main_logger.info(f"   Code de sortie: {exitstatus}")
        self.logger.main_logger.info("=" * 80)
        
    def pytest_collection_modifyitems(self, config, items):
        """Appelé après la collecte des tests."""
        self.logger.main_logger.info(f"📊 {len(items)} tests collectés")
        
        # Grouper les tests par module
        modules = {}
        for item in items:
            module_name = item.module.__name__
            if module_name not in modules:
                modules[module_name] = []
            modules[module_name].append(item.name)
            
        # Logger les modules et leurs tests
        for module, tests in modules.items():
            self.logger.main_logger.info(f"   📁 {module}: {len(tests)} tests")
            
    def pytest_runtest_logstart(self, nodeid, location):
        """Appelé au début de chaque test."""
        self.test_start_time = time.time()
        test_name = nodeid.split("::")[-1]
        module_name = location[0]
        self.logger.log_test_start(test_name, module_name)
        
    def pytest_runtest_logfinish(self, nodeid, location):
        """Appelé à la fin de chaque test."""
        pass  # Le résultat sera géré par les autres hooks
        
    def pytest_runtest_logreport(self, report):
        """Appelé pour chaque phase de test (setup, call, teardown)."""
        if report.when == "call":  # Seulement pour la phase d'exécution du test
            test_name = report.nodeid.split("::")[-1]
            duration = getattr(report, 'duration', 0)
            
            if report.outcome == "passed":
                self.stats['passed'] += 1
                self.logger.log_test_pass(test_name, duration)
                
            elif report.outcome == "failed":
                self.stats['failed'] += 1
                error_msg = str(report.longrepr) if report.longrepr else "Erreur inconnue"
                # Tronquer l'erreur si elle est trop longue
                if len(error_msg) > 500:
                    error_msg = error_msg[:500] + "... (tronqué)"
                self.logger.log_test_fail(test_name, error_msg, duration)
                
            elif report.outcome == "skipped":
                self.stats['skipped'] += 1
                reason = report.longrepr[2] if report.longrepr else "Raison inconnue"
                self.logger.log_test_skip(test_name, reason)


def pytest_configure(config):
    """Configure le plugin pytest."""
    config.pluginmanager.register(TestResultsPlugin(), "test_results_logger")


def pytest_unconfigure(config):
    """Nettoie le plugin à la fin."""
    pass
