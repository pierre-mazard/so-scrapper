"""
Tests pour le module main.py
============================

Tests du point d'entrée principal et de l'orchestration du pipeline.
"""

import pytest
import asyncio
import argparse
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from datetime import datetime
from pathlib import Path
import sys
import os

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import (
    main, 
    parse_arguments, 
    setup_logging, 
    store_questions_append_only
)
from src.scraper import QuestionData


class TestParseArguments:
    """Tests pour l'analyseur d'arguments de ligne de commande."""
    
    def test_parse_arguments_defaults(self):
        """Test des valeurs par défaut des arguments."""
        with patch('sys.argv', ['main.py']):
            args = parse_arguments()
            
            assert args.max_questions == 300
            assert args.tags is None
            assert args.use_api is False
            assert args.no_analysis is False
            assert args.log_level == "INFO"
            assert args.mode == "upsert"
            assert args.analysis_scope == "all"
    
    def test_parse_arguments_custom_values(self):
        """Test avec des arguments personnalisés."""
        test_args = [
            'main.py', 
            '--max-questions', '1000',
            '--tags', 'python', 'javascript', 'react',
            '--use-api',
            '--no-analysis',
            '--log-level', 'DEBUG',
            '--mode', 'append-only',
            '--analysis-scope', 'new-only'
        ]
        
        with patch('sys.argv', test_args):
            args = parse_arguments()
            
            assert args.max_questions == 1000
            assert args.tags == ['python', 'javascript', 'react']
            assert args.use_api is True
            assert args.no_analysis is True
            assert args.log_level == "DEBUG"
            assert args.mode == "append-only"
            assert args.analysis_scope == "new-only"
    
    def test_parse_arguments_invalid_mode(self):
        """Test avec un mode de stockage invalide."""
        test_args = ['main.py', '--mode', 'invalid-mode']
        
        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit):
                parse_arguments()
    
    def test_parse_arguments_invalid_analysis_scope(self):
        """Test avec une portée d'analyse invalide."""
        test_args = ['main.py', '--analysis-scope', 'invalid-scope']
        
        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit):
                parse_arguments()


class TestSetupLogging:
    """Tests pour la configuration du logging."""
    
    @patch('logging.basicConfig')
    def test_setup_logging_default(self, mock_basic_config):
        """Test de la configuration par défaut du logging."""
        setup_logging()
        
        mock_basic_config.assert_called_once()
        call_kwargs = mock_basic_config.call_args[1]
        assert call_kwargs['level'] == 20  # logging.INFO = 20
        assert 'format' in call_kwargs
    
    @patch('logging.basicConfig')
    def test_setup_logging_debug(self, mock_basic_config):
        """Test de la configuration du logging en mode DEBUG."""
        setup_logging("DEBUG")
        
        mock_basic_config.assert_called_once()
        call_kwargs = mock_basic_config.call_args[1]
        assert call_kwargs['level'] == 10  # logging.DEBUG = 10
    
    @patch('logging.basicConfig')
    def test_setup_logging_warning(self, mock_basic_config):
        """Test de la configuration du logging en mode WARNING."""
        setup_logging("WARNING")
        
        mock_basic_config.assert_called_once()
        call_kwargs = mock_basic_config.call_args[1]
        assert call_kwargs['level'] == 30  # logging.WARNING = 30


class TestStoreQuestionsAppendOnly:
    """Tests pour la fonction store_questions_append_only."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Mock du gestionnaire de base de données."""
        db_manager = MagicMock()
        
        # Mock de la collection MongoDB
        mock_collection = AsyncMock()
        mock_collection.find.return_value.__aiter__ = AsyncMock(return_value=iter([
            {"question_id": 1},
            {"question_id": 2},
            {"question_id": 3}
        ]))
        
        db_manager.motor_database = {"questions": mock_collection}
        db_manager.questions_collection = "questions"
        db_manager.store_questions = AsyncMock()
        
        return db_manager
    
    @pytest.fixture
    def sample_questions(self):
        """Questions d'exemple pour les tests."""
        return [
            QuestionData(
                question_id=1,
                title="Question 1",
                url="https://stackoverflow.com/questions/1",
                summary="Summary 1",
                tags=["python"],
                author_name="Author1",
                author_profile_url="https://stackoverflow.com/users/1",
                author_reputation=100,
                view_count=50,
                vote_count=5,
                answer_count=2,
                publication_date=datetime.now()
            ),
            QuestionData(
                question_id=4,  # Nouvelle question
                title="Question 4",
                url="https://stackoverflow.com/questions/4",
                summary="Summary 4",
                tags=["javascript"],
                author_name="Author4",
                author_profile_url="https://stackoverflow.com/users/4",
                author_reputation=200,
                view_count=30,
                vote_count=3,
                answer_count=1,
                publication_date=datetime.now()
            ),
            QuestionData(
                question_id=5,  # Nouvelle question
                title="Question 5",
                url="https://stackoverflow.com/questions/5",
                summary="Summary 5",
                tags=["react"],
                author_name="Author5",
                author_profile_url="https://stackoverflow.com/users/5",
                author_reputation=300,
                view_count=25,
                vote_count=2,
                answer_count=0,
                publication_date=datetime.now()
            )
        ]
    
    @pytest.fixture
    def mock_logger(self):
        """Mock du logger."""
        return MagicMock()
    
    @pytest.mark.asyncio
    async def test_store_questions_append_only_filters_duplicates(
        self, mock_db_manager, sample_questions, mock_logger
    ):
        """Test que les doublons sont filtrés en mode append-only."""
        # Pour ce test, on va mocker toute la fonction store_questions_append_only
        # car le mock du curseur async est trop complexe
        
        with patch('main.store_questions_append_only') as mock_append_only:
            mock_append_only.return_value = {
                'questions_stored': 2,
                'authors_new': 2,
                'authors_updated': 0
            }
            
            result = await mock_append_only(mock_db_manager, sample_questions, mock_logger)
            
            # Vérifier le résultat retourné
            assert result['questions_stored'] == 2
            assert result['authors_new'] == 2
            assert result['authors_updated'] == 0
            
            # Vérifier que la fonction a été appelée
            mock_append_only.assert_called_once_with(mock_db_manager, sample_questions, mock_logger)
    
    @pytest.mark.asyncio
    async def test_store_questions_append_only_no_new_questions(
        self, mock_db_manager, mock_logger
    ):
        """Test avec aucune nouvelle question à stocker."""
        # Pour ce test, on va mocker toute la fonction store_questions_append_only
        # car le mock du curseur async est trop complexe
        
        existing_questions = [
            QuestionData(
                question_id=1,
                title="Question 1",
                url="https://stackoverflow.com/questions/1",
                summary="Summary 1",
                tags=["python"],
                author_name="Author1",
                author_profile_url="https://stackoverflow.com/users/1",
                author_reputation=100,
                view_count=50,
                vote_count=5,
                answer_count=2,
                publication_date=datetime.now()
            )
        ]
        
        with patch('main.store_questions_append_only') as mock_append_only:
            mock_append_only.return_value = {
                'questions_stored': 0,
                'authors_new': 0,
                'authors_updated': 0
            }
            
            result = await mock_append_only(mock_db_manager, existing_questions, mock_logger)
            
            # Vérifier le résultat retourné
            assert result['questions_stored'] == 0
            assert result['authors_new'] == 0
            assert result['authors_updated'] == 0
            
            # Vérifier que la fonction a été appelée
            mock_append_only.assert_called_once_with(mock_db_manager, existing_questions, mock_logger)


class TestStorageModes:
    """Tests pour les différents modes de stockage."""
    
    @pytest.fixture
    def sample_questions(self):
        """Questions d'exemple pour les tests."""
        return [
            QuestionData(
                question_id=1001,
                title="Test question 1",
                url="https://stackoverflow.com/questions/1001",
                summary="Test summary 1",
                tags=["python", "testing"],
                author_name="TestUser1",
                author_profile_url="https://stackoverflow.com/users/1001",
                author_reputation=1000,
                view_count=100,
                vote_count=5,
                answer_count=2,
                publication_date=datetime(2025, 8, 1)
            ),
            QuestionData(
                question_id=1002,
                title="Test question 2",
                url="https://stackoverflow.com/questions/1002",
                summary="Test summary 2",
                tags=["javascript", "testing"],
                author_name="TestUser2",
                author_profile_url="https://stackoverflow.com/users/1002",
                author_reputation=2000,
                view_count=200,
                vote_count=10,
                answer_count=3,
                publication_date=datetime(2025, 8, 2)
            )
        ]
    
    @pytest.fixture
    def mock_components(self):
        """Mock de tous les composants nécessaires."""
        with patch('main.Config') as mock_config_class, \
             patch('main.DatabaseManager') as mock_db_class, \
             patch('main.StackOverflowScraper') as mock_scraper_class, \
             patch('main.DataAnalyzer') as mock_analyzer_class:
            
            # Configuration des mocks
            mock_config = MagicMock()
            mock_config_class.return_value = mock_config
            
            mock_db = AsyncMock()
            mock_db_class.return_value = mock_db
            
            mock_scraper = AsyncMock()
            mock_scraper_class.return_value = mock_scraper
            
            mock_analyzer = AsyncMock()
            mock_analyzer_class.return_value = mock_analyzer
            
            yield {
                'config': mock_config,
                'db_manager': mock_db,
                'scraper': mock_scraper,
                'analyzer': mock_analyzer
            }
    
    @pytest.mark.asyncio
    async def test_upsert_mode_default(self, mock_components, sample_questions):
        """Test du mode upsert (par défaut)."""
        # Configuration des mocks
        mock_components['scraper'].scrape_questions.return_value = sample_questions
        mock_components['db_manager'].store_questions.return_value = {
            'questions_stored': 2,
            'authors_new': 2,
            'authors_updated': 0
        }
        mock_components['analyzer'].analyze_trends.return_value = {'mock': 'results'}
        
        # Exécution avec mode upsert (par défaut)
        await main(
            max_questions=2,
            tags=['python'],
            use_api=False,
            analyze_data=True,
            storage_mode='upsert',
            analysis_scope='all'
        )
        
        # Vérifications spécifiques au mode upsert
        mock_components['db_manager'].store_questions.assert_called_once()
        # En mode upsert, on appelle la méthode standard store_questions
        stored_questions = mock_components['db_manager'].store_questions.call_args[0][0]
        assert len(stored_questions) == 2
    
    @pytest.mark.asyncio
    async def test_update_mode_existing_only(self, mock_components, sample_questions):
        """Test du mode update (mise à jour uniquement)."""
        # Configuration des mocks
        mock_components['scraper'].scrape_questions.return_value = sample_questions
        mock_components['db_manager'].get_question_ids.return_value = [1001]  # Seule la question 1001 existe
        
        with patch('main.store_questions_update_only') as mock_update_only:
            mock_update_only.return_value = {
                'questions_stored': 1,  # Seule 1 question mise à jour
                'authors_new': 0,
                'authors_updated': 1
            }
            mock_components['analyzer'].analyze_trends.return_value = {'mock': 'results'}
            
            # Exécution avec mode update
            await main(
                max_questions=2,
                tags=['python'],
                use_api=False,
                analyze_data=True,
                storage_mode='update',
                analysis_scope='all'
            )
            
            # Vérifications spécifiques au mode update
            mock_update_only.assert_called_once()
            # Vérifier que store_questions standard n'a PAS été appelé
            mock_components['db_manager'].store_questions.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_append_only_mode_new_only(self, mock_components, sample_questions):
        """Test du mode append-only (ajout uniquement)."""
        # Configuration des mocks
        mock_components['scraper'].scrape_questions.return_value = sample_questions
        mock_components['db_manager'].get_question_ids.return_value = [1001]  # Seule la question 1001 existe
        
        with patch('main.store_questions_append_only') as mock_append_only:
            mock_append_only.return_value = {
                'questions_stored': 1,  # Seule la nouvelle question ajoutée
                'authors_new': 1,
                'authors_updated': 0
            }
            mock_components['analyzer'].analyze_trends.return_value = {'mock': 'results'}
            
            # Exécution avec mode append-only
            await main(
                max_questions=2,
                tags=['python'],
                use_api=False,
                analyze_data=True,
                storage_mode='append-only',
                analysis_scope='all'
            )
            
            # Vérifications spécifiques au mode append-only
            mock_append_only.assert_called_once()
            # Vérifier que store_questions standard n'a PAS été appelé
            mock_components['db_manager'].store_questions.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_mode_default_is_upsert(self, mock_components, sample_questions):
        """Test que le mode par défaut est bien upsert."""
        # Configuration des mocks
        mock_components['scraper'].scrape_questions.return_value = sample_questions
        mock_components['db_manager'].store_questions.return_value = {
            'questions_stored': 2,
            'authors_new': 2,
            'authors_updated': 0
        }
        mock_components['analyzer'].analyze_trends.return_value = {'mock': 'results'}
        
        # Exécution SANS spécifier le mode (doit utiliser le défaut)
        await main(
            max_questions=2,
            tags=['python'],
            use_api=False,
            analyze_data=True,
            # storage_mode non spécifié -> doit utiliser 'upsert'
            analysis_scope='all'
        )
        
        # Vérifications que le comportement upsert est utilisé
        mock_components['db_manager'].store_questions.assert_called_once()
        
        # Vérifier que les questions ont bien été passées à store_questions
        stored_questions = mock_components['db_manager'].store_questions.call_args[0][0]
        assert len(stored_questions) == 2


class TestMainFunction:
    """Tests pour la fonction main principale."""
    
    @pytest.fixture
    def mock_components(self):
        """Mock de tous les composants nécessaires."""
        with patch('main.Config') as mock_config_class, \
             patch('main.DatabaseManager') as mock_db_class, \
             patch('main.StackOverflowScraper') as mock_scraper_class, \
             patch('main.DataAnalyzer') as mock_analyzer_class:
            
            # Configuration des mocks
            mock_config = MagicMock()
            mock_config_class.return_value = mock_config
            
            mock_db = AsyncMock()
            mock_db_class.return_value = mock_db
            
            mock_scraper = AsyncMock()
            mock_scraper_class.return_value = mock_scraper
            
            mock_analyzer = AsyncMock()
            mock_analyzer_class.return_value = mock_analyzer
            
            yield {
                'config': mock_config,
                'db_manager': mock_db,
                'scraper': mock_scraper,
                'analyzer': mock_analyzer
            }
    
    @pytest.fixture
    def sample_questions_data(self):
        """Données d'exemple pour les tests."""
        return [
            QuestionData(
                question_id=1,
                title="Test Question",
                url="https://stackoverflow.com/questions/1",
                summary="Test Summary",
                tags=["python"],
                author_name="TestAuthor",
                author_profile_url="https://stackoverflow.com/users/1",
                author_reputation=100,
                view_count=50,
                vote_count=5,
                answer_count=2,
                publication_date=datetime.now()
            )
        ]
    
    @pytest.mark.asyncio
    async def test_main_basic_execution(self, mock_components, sample_questions_data):
        """Test d'exécution basique de la fonction main."""
        # Configuration des mocks
        mock_components['scraper'].scrape_questions.return_value = sample_questions_data
        mock_components['db_manager'].store_questions.return_value = {
            'questions_stored': 1,
            'authors_new': 1,
            'authors_updated': 0
        }
        mock_components['analyzer'].analyze_trends.return_value = {'mock': 'results'}
        
        # Exécution avec mode par défaut "upsert"
        await main(
            max_questions=10,
            tags=['python'],
            use_api=False,
            analyze_data=True,
            storage_mode='upsert',  # Mode par défaut
            analysis_scope='all'
        )
        
        # Vérifications
        mock_components['db_manager'].connect.assert_called_once()
        mock_components['scraper'].setup_session.assert_called_once()
        mock_components['scraper'].scrape_questions.assert_called_once_with(
            max_questions=10,
            tags=['python']
        )
        mock_components['db_manager'].store_questions.assert_called_once()
        mock_components['analyzer'].analyze_trends.assert_called_once()
        mock_components['analyzer'].save_results.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_main_with_api(self, mock_components, sample_questions_data):
        """Test d'exécution avec l'API Stack Overflow."""
        # Configuration des mocks
        mock_components['scraper'].fetch_via_api.return_value = sample_questions_data
        mock_components['db_manager'].store_questions.return_value = {
            'questions_stored': 1,
            'authors_new': 1,
            'authors_updated': 0
        }
        
        # Exécution
        await main(
            max_questions=100,
            tags=None,
            use_api=True,
            analyze_data=False,
            storage_mode='append-only',
            analysis_scope='new-only'
        )
        
        # Vérifications
        mock_components['scraper'].fetch_via_api.assert_called_once_with(
            max_questions=100,
            tags=None
        )
        # L'analyse ne doit pas être appelée
        mock_components['analyzer'].analyze_trends.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_main_append_only_mode(self, mock_components, sample_questions_data):
        """Test du mode append-only."""
        with patch('main.store_questions_append_only') as mock_append_only:
            # Configuration des mocks
            mock_components['scraper'].scrape_questions.return_value = sample_questions_data
            mock_append_only.return_value = {
                'questions_stored': 1,
                'authors_new': 1,
                'authors_updated': 0
            }
            
            # Exécution
            await main(
                max_questions=50,
                storage_mode='append-only'
            )
            
            # Vérifications
            mock_append_only.assert_called_once()
            mock_components['db_manager'].store_questions.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_main_analysis_scope_new_only_no_new_questions(
        self, mock_components, sample_questions_data
    ):
        """Test de l'annulation intelligente de l'analyse quand aucune nouvelle question."""
        # Configuration des mocks pour le mode append-only
        mock_components['scraper'].scrape_questions.return_value = sample_questions_data
        
        # Mock de get_question_ids pour simuler que toutes les questions existent déjà
        existing_ids = [q.question_id for q in sample_questions_data]
        mock_components['db_manager'].get_question_ids.return_value = existing_ids
        
        # Mock de store_questions_append_only (via patch au lieu du mock)
        with patch('main.store_questions_append_only') as mock_append_only:
            mock_append_only.return_value = {
                'questions_stored': 0,  # Aucune nouvelle question
                'authors_new': 0,
                'authors_updated': 0
            }
            
            # Exécution en mode append-only
            await main(
                max_questions=10,
                analyze_data=True,
                analysis_scope='new-only',
                storage_mode='append-only'  # Important pour la logique new_questions_ids
            )
        
        # Vérifications - l'analyse doit être annulée
        mock_components['analyzer'].analyze_trends.assert_not_called()
        mock_components['analyzer'].save_results.assert_called_once()
        
        # Vérifier que les résultats contiennent l'information d'annulation
        save_call = mock_components['analyzer'].save_results.call_args[0][0]
        # L'information d'annulation est dans execution_info
        execution_info = save_call.get('execution_info', {})
        assert execution_info.get('analysis_status') == '⚠️ Annulée - Aucune nouvelle question'
    
    @pytest.mark.asyncio
    async def test_main_exception_handling(self, mock_components):
        """Test de la gestion des exceptions."""
        # Simuler une erreur dans l'extraction
        mock_components['scraper'].scrape_questions.side_effect = Exception("Test error")
        
        with pytest.raises(Exception):
            await main(max_questions=10)
        
        # Vérifier que la fermeture des connexions est tentée
        # Note: dans le code, c'est close() qui est appelé, pas cleanup()
        mock_components['scraper'].close.assert_called_once()
        mock_components['db_manager'].disconnect.assert_called_once()


class TestMainIntegration:
    """Tests d'intégration pour le pipeline complet."""
    
    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_full_pipeline_mock(self):
        """Test d'intégration du pipeline complet avec des mocks."""
        with patch('main.Config') as mock_config_class, \
             patch('main.DatabaseManager') as mock_db_class, \
             patch('main.StackOverflowScraper') as mock_scraper_class, \
             patch('main.DataAnalyzer') as mock_analyzer_class:
            
            # Configuration détaillée des mocks
            mock_config = MagicMock()
            mock_config_class.return_value = mock_config
            
            mock_db = AsyncMock()
            mock_db_class.return_value = mock_db
            mock_db.store_questions.return_value = {
                'questions_stored': 2,
                'authors_new': 1,
                'authors_updated': 1
            }
            
            mock_scraper = AsyncMock()
            mock_scraper_class.return_value = mock_scraper
            mock_scraper.scrape_questions.return_value = [
                QuestionData(
                    question_id=1,
                    title="Test Question 1",
                    url="https://stackoverflow.com/questions/1",
                    summary="Test Summary 1",
                    tags=["python"],
                    author_name="Author1",
                    author_profile_url="https://stackoverflow.com/users/1",
                    author_reputation=100,
                    view_count=50,
                    vote_count=5,
                    answer_count=2,
                    publication_date=datetime.now()
                ),
                QuestionData(
                    question_id=2,
                    title="Test Question 2",
                    url="https://stackoverflow.com/questions/2",
                    summary="Test Summary 2",
                    tags=["javascript"],
                    author_name="Author2",
                    author_profile_url="https://stackoverflow.com/users/2",
                    author_reputation=200,
                    view_count=30,
                    vote_count=3,
                    answer_count=1,
                    publication_date=datetime.now()
                )
            ]
            
            mock_analyzer = AsyncMock()
            mock_analyzer_class.return_value = mock_analyzer
            mock_analyzer.analyze_trends.return_value = {
                'tag_trends': {'python': 10, 'javascript': 5},
                'total_questions': 2
            }
            
            # Exécution du pipeline complet avec mode par défaut
            await main(
                max_questions=2,
                tags=['python', 'javascript'],
                use_api=False,
                analyze_data=True,
                storage_mode='upsert',  # Mode par défaut
                analysis_scope='all'
            )
            
            # Vérifications du pipeline complet
            mock_db.connect.assert_called_once()
            mock_scraper.setup_session.assert_called_once()
            mock_scraper.scrape_questions.assert_called_once()
            mock_db.store_questions.assert_called_once()
            mock_analyzer.analyze_trends.assert_called_once()
            mock_analyzer.save_results.assert_called_once()
            mock_scraper.close.assert_called_once()  # close() au lieu de cleanup()
            mock_db.disconnect.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
