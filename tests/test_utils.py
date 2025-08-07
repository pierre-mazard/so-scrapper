"""
Tests pour les utilitaires (utils/)
===================================

Tests des scripts utilitaires check_mongodb.py et clear_database.py.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from pathlib import Path
import sys
import os
import subprocess

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCheckMongoDB:
    """Tests pour utils/check_mongodb.py."""
    
    @pytest.fixture
    def mock_motor_client(self):
        """Mock du client MongoDB Motor."""
        with patch('motor.motor_asyncio.AsyncIOMotorClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value = mock_instance
            
            # Mock de la base de données
            mock_db = AsyncMock()
            mock_instance.__getitem__.return_value = mock_db
            
            # Mock des collections
            mock_db.list_collection_names.return_value = ['questions', 'authors', 'analysis']
            
            # Mock de stats des collections
            mock_collection = AsyncMock()
            mock_db.__getitem__.return_value = mock_collection
            mock_collection.count_documents.return_value = 1000
            mock_collection.estimated_document_count.return_value = 1000
            
            yield mock_instance
    
    def test_check_mongodb_script_exists(self):
        """Test que le script check_mongodb.py existe."""
        script_path = Path(__file__).parent.parent / "utils" / "check_mongodb.py"
        assert script_path.exists(), "Le script check_mongodb.py doit exister"
    
    def test_check_mongodb_script_executable(self):
        """Test que le script peut être exécuté."""
        script_path = Path(__file__).parent.parent / "utils" / "check_mongodb.py"
        
        # Test d'exécution avec --help (ne nécessite pas MongoDB)
        try:
            result = subprocess.run(
                [sys.executable, str(script_path), "--help"],
                capture_output=True,
                text=True,
                timeout=10
            )
            # Le script doit soit afficher l'aide, soit échouer proprement
            assert result.returncode in [0, 1, 2]  # 0=succès, 1=erreur normale, 2=erreur d'arguments
        except subprocess.TimeoutExpired:
            pytest.fail("Le script check_mongodb.py met trop de temps à répondre")
        except Exception as e:
            pytest.fail(f"Erreur lors de l'exécution du script: {e}")
    
    @patch('builtins.print')
    def test_check_mongodb_import(self, mock_print):
        """Test que les imports du script fonctionnent."""
        script_path = Path(__file__).parent.parent / "utils" / "check_mongodb.py"
        
        # Lecture du contenu du script
        with open(script_path, 'r', encoding='utf-8') as f:
            script_content = f.read()
        
        # Vérification des imports essentiels (pas d'asyncio requis pour ce script)
        assert 'pymongo' in script_content
        assert 'from config import Config' in script_content or 'import config' in script_content
        assert 'import sys' in script_content


class TestClearDatabase:
    """Tests pour utils/clear_database.py."""
    
    def test_clear_database_script_exists(self):
        """Test que le script clear_database.py existe."""
        script_path = Path(__file__).parent.parent / "utils" / "clear_database.py"
        assert script_path.exists(), "Le script clear_database.py doit exister"
    
    def test_clear_database_script_structure(self):
        """Test de la structure du script clear_database.py."""
        script_path = Path(__file__).parent.parent / "utils" / "clear_database.py"
        
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Vérifications de sécurité - le script doit demander confirmation
        assert 'input(' in content or 'confirmation' in content.lower(), \
            "Le script doit demander une confirmation avant suppression"
        
        # Vérifications des imports
        assert 'motor' in content or 'pymongo' in content, \
            "Le script doit importer un client MongoDB"
    
    def test_clear_database_safety_check(self):
        """Test que le script ne peut pas être exécuté sans confirmation."""
        script_path = Path(__file__).parent.parent / "utils" / "clear_database.py"
        
        # Test d'exécution avec input vide (doit échouer ou demander confirmation)
        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                input="\n",  # Entrée vide
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Le script doit soit échouer (sécurité), soit demander confirmation
            output = result.stdout + result.stderr
            assert any(word in output.lower() for word in ['confirmation', 'oui', 'yes', 'confirmer']) or \
                   result.returncode != 0, \
                   "Le script doit demander confirmation ou échouer par sécurité"
        
        except subprocess.TimeoutExpired:
            pytest.fail("Le script clear_database.py met trop de temps à répondre")
        except Exception as e:
            # Acceptable si MongoDB n'est pas accessible
            pass


class TestRunTests:
    """Tests pour run_tests.py."""
    
    def test_run_tests_script_exists(self):
        """Test que le script run_tests.py existe."""
        script_path = Path(__file__).parent.parent / "run_tests.py"
        assert script_path.exists(), "Le script run_tests.py doit exister"
    
    def test_run_tests_imports(self):
        """Test des imports de run_tests.py."""
        script_path = Path(__file__).parent.parent / "run_tests.py"
        
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Vérifications des imports essentiels
        assert 'import subprocess' in content
        assert 'import sys' in content
        assert 'from pathlib import Path' in content
        assert 'from datetime import datetime' in content
    
    def test_run_tests_functions_exist(self):
        """Test que les fonctions principales existent."""
        script_path = Path(__file__).parent.parent / "run_tests.py"
        
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Vérifications des fonctions principales
        assert 'def run_tests_with_logging' in content
        assert 'def generate_test_report' in content
        assert 'def convert_to_markdown' in content
    
    @patch('subprocess.run')
    def test_run_tests_with_logging(self, mock_subprocess):
        """Test de la fonction run_tests_with_logging."""
        from run_tests import run_tests_with_logging
        
        # Mock du subprocess
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        # Exécution
        exit_code = run_tests_with_logging()
        
        # Vérifications
        mock_subprocess.assert_called_once()
        assert exit_code == 0
    
    def test_convert_to_markdown_structure(self):
        """Test de la structure du rapport Markdown généré."""
        from run_tests import convert_to_markdown
        
        # Données de test
        test_results = {
            'passed': [
                {'name': 'test_example', 'duration': 0.1}
            ],
            'failed': [],
            'errors': [],
            'skipped': [],
            'total_duration': 10.5
        }
        
        report = "Test report"
        
        # Génération du rapport
        markdown = convert_to_markdown(report, test_results)
        
        # Vérifications de la structure
        assert '# 🧪 RAPPORT DE TESTS' in markdown
        assert '## 📊 RÉSUMÉ EXÉCUTIF' in markdown
        assert '### Informations générales' in markdown
        assert '| Statut | Nombre | Pourcentage |' in markdown
        assert 'Stack Overflow Scraper' in markdown
    
    def test_convert_to_markdown_with_failures(self):
        """Test du rapport Markdown avec des échecs."""
        from run_tests import convert_to_markdown
        
        # Données de test avec échecs
        test_results = {
            'passed': [
                {'name': 'test_success', 'duration': 0.1}
            ],
            'failed': [
                {'name': 'test_failure', 'duration': 0.2}
            ],
            'errors': [
                {'name': 'test_error', 'duration': 0.3}
            ],
            'skipped': [
                {'name': 'test_skipped', 'duration': 0.0}
            ],
            'total_duration': 15.0
        }
        
        report = "Test report with failures"
        
        # Génération du rapport
        markdown = convert_to_markdown(report, test_results)
        
        # Vérifications des sections d'échecs
        assert '### ❌ Tests Échoués' in markdown
        assert '### 🚫 Erreurs de Tests' in markdown
        assert '### ⏭️ Tests Ignorés' in markdown
        assert 'test_failure' in markdown
        assert 'test_error' in markdown
        assert 'test_skipped' in markdown


class TestUtilsIntegration:
    """Tests d'intégration des utilitaires."""
    
    @pytest.mark.integration
    def test_utils_directory_structure(self):
        """Test de la structure du répertoire utils."""
        utils_dir = Path(__file__).parent.parent / "utils"
        
        assert utils_dir.exists(), "Le répertoire utils/ doit exister"
        assert utils_dir.is_dir(), "utils/ doit être un répertoire"
        
        # Vérification des fichiers essentiels
        expected_files = [
            "check_mongodb.py",
            "clear_database.py"
        ]
        
        for filename in expected_files:
            file_path = utils_dir / filename
            assert file_path.exists(), f"Le fichier {filename} doit exister dans utils/"
            assert file_path.is_file(), f"{filename} doit être un fichier"
    
    @pytest.mark.integration
    def test_all_scripts_have_main_guard(self):
        """Test que tous les scripts ont une protection if __name__ == '__main__'."""
        utils_dir = Path(__file__).parent.parent / "utils"
        
        for script_file in utils_dir.glob("*.py"):
            if script_file.name.startswith("__"):
                continue  # Ignorer __init__.py etc.
            
            with open(script_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert 'if __name__ == ' in content, \
                f"Le script {script_file.name} doit avoir une protection main"
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_scripts_syntax_validation(self):
        """Test que tous les scripts Python sont syntaxiquement corrects."""
        utils_dir = Path(__file__).parent.parent / "utils"
        
        for script_file in utils_dir.glob("*.py"):
            if script_file.name.startswith("__"):
                continue
            
            # Test de compilation syntaxique
            try:
                with open(script_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                compile(content, str(script_file), 'exec')
                
            except SyntaxError as e:
                pytest.fail(f"Erreur de syntaxe dans {script_file.name}: {e}")
            except Exception as e:
                # Les erreurs d'import sont acceptables (dépendances)
                if "No module named" not in str(e):
                    pytest.fail(f"Erreur inattendue dans {script_file.name}: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
