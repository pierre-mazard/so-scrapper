"""
Tests d'intégration end-to-end
==============================

Tests complets du pipeline principal avec simulation réaliste.
"""

import pytest
import asyncio
import tempfile
import shutil
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from pathlib import Path
import sys
import os
from datetime import datetime, timedelta

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import main
from src.scraper import QuestionData


class TestEndToEndPipeline:
    """Tests end-to-end complets du pipeline."""
    
    @pytest.fixture
    def sample_realistic_questions(self):
        """Questions réalistes pour les tests end-to-end."""
        base_time = datetime.now()
        
        return [
            QuestionData(
                question_id=12345,
                title="How to implement async/await in Python?",
                url="https://stackoverflow.com/questions/12345",
                summary="I'm trying to understand how to properly use async/await in Python. I have a function that needs to make multiple API calls...",
                tags=["python", "async-await", "asyncio"],
                author_name="PythonDeveloper",
                author_profile_url="https://stackoverflow.com/users/123",
                author_reputation=1540,
                view_count=243,
                vote_count=12,
                answer_count=3,
                publication_date=base_time - timedelta(hours=2)
            ),
            QuestionData(
                question_id=12346,
                title="React useState hook not updating state",
                url="https://stackoverflow.com/questions/12346",
                summary="I'm having trouble with React useState hook. The state doesn't seem to update immediately after calling setState...",
                tags=["javascript", "reactjs", "hooks", "state"],
                author_name="ReactNewbie",
                author_profile_url="https://stackoverflow.com/users/456",
                author_reputation=89,
                view_count=156,
                vote_count=5,
                answer_count=2,
                publication_date=base_time - timedelta(hours=1)
            ),
            QuestionData(
                question_id=12347,
                title="SQL JOIN optimization for large datasets",
                url="https://stackoverflow.com/questions/12347",
                summary="I need to optimize a complex SQL query with multiple JOINs. The query works but is very slow on large datasets...",
                tags=["sql", "performance", "join", "optimization"],
                author_name="DatabaseExpert",
                author_profile_url="https://stackoverflow.com/users/789",
                author_reputation=3245,
                view_count=412,
                vote_count=18,
                answer_count=4,
                publication_date=base_time - timedelta(minutes=30)
            ),
            QuestionData(
                question_id=12348,
                title="Docker container networking issues",
                url="https://stackoverflow.com/questions/12348",
                summary="I'm having problems with Docker container networking. Containers can't communicate with each other...",
                tags=["docker", "networking", "containers", "devops"],
                author_name="DevOpsEngineer",
                author_profile_url="https://stackoverflow.com/users/101",
                author_reputation=2156,
                view_count=87,
                vote_count=7,
                answer_count=1,
                publication_date=base_time - timedelta(minutes=10)
            ),
            QuestionData(
                question_id=12349,
                title="Machine Learning model overfitting",
                url="https://stackoverflow.com/questions/12349",
                summary="My ML model is overfitting the training data. What techniques can I use to prevent this?",
                tags=["machine-learning", "python", "tensorflow", "overfitting"],
                author_name="MLResearcher",
                author_profile_url="https://stackoverflow.com/users/202",
                author_reputation=567,
                view_count=298,
                vote_count=9,
                answer_count=3,
                publication_date=base_time - timedelta(minutes=5)
            )
        ]
    
    @pytest.fixture
    def temp_output_dir(self):
        """Répertoire temporaire pour les outputs de test."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_complete_pipeline_scraping_mode(self, sample_realistic_questions, temp_output_dir):
        """Test complet du pipeline en mode scraping."""
        with patch('main.Config') as mock_config_class, \
             patch('main.DatabaseManager') as mock_db_class, \
             patch('main.StackOverflowScraper') as mock_scraper_class, \
             patch('main.DataAnalyzer') as mock_analyzer_class, \
             patch('pathlib.Path.mkdir'), \
             patch('builtins.open', mock_open()):
            
            # === Configuration des mocks détaillés ===
            
            # Config
            mock_config = MagicMock()
            mock_config.database_config = MagicMock()
            mock_config.scraper_config.__dict__ = {'timeout': 30, 'delay': 1}
            mock_config.api_config.__dict__ = {'key': '', 'rate_limit': 300}
            mock_config_class.return_value = mock_config
            
            # Database Manager
            mock_db = AsyncMock()
            mock_db_class.return_value = mock_db
            mock_db.store_questions.return_value = {
                'questions_stored': 5,
                'authors_new': 4,
                'authors_updated': 1
            }
            
            # Scraper
            mock_scraper = AsyncMock()
            mock_scraper_class.return_value = mock_scraper
            mock_scraper.scrape_questions.return_value = sample_realistic_questions
            
            # Analyzer
            mock_analyzer = AsyncMock()
            mock_analyzer_class.return_value = mock_analyzer
            mock_analyzer.analyze_trends.return_value = {
                'tag_trends': {
                    'trending_tags': [
                        {'tag': 'python', 'total_questions': 2, 'growth_rate': 15.5},
                        {'tag': 'javascript', 'total_questions': 1, 'growth_rate': 8.2},
                        {'tag': 'sql', 'total_questions': 1, 'growth_rate': 5.1}
                    ]
                },
                'temporal_patterns': {
                    'peak_hour': 14,
                    'peak_day': 'Tuesday'
                },
                'content_analysis': {
                    'title_keywords': [['python', 0.15], ['react', 0.12], ['sql', 0.10]],
                    'summary_keywords': [['function', 0.08], ['problem', 0.07], ['help', 0.06]],
                    'title_sentiment': {'positive': 1, 'negative': 2, 'neutral': 2, 'average': -0.1},
                    'summary_sentiment': {'positive': 3, 'negative': 1, 'neutral': 1, 'average': 0.2}
                },
                'author_analysis': {
                    'top_contributors': [
                        {'name': 'DatabaseExpert', 'reputation': 3245, 'questions': 1},
                        {'name': 'DevOpsEngineer', 'reputation': 2156, 'questions': 1}
                    ]
                },
                'general_stats': {
                    'total_questions': 5,
                    'avg_views': 239.2,
                    'avg_votes': 10.2,
                    'response_rate': 0.8
                }
            }
            
            # === Exécution du pipeline ===
            await main(
                max_questions=10,
                tags=['python', 'javascript'],
                use_api=False,
                analyze_data=True,
                storage_mode='update',
                analysis_scope='all'
            )
            
            # === Vérifications complètes ===
            
            # 1. Initialisation
            mock_config_class.assert_called_once()
            mock_db_class.assert_called_once_with(mock_config.database_config)
            mock_scraper_class.assert_called_once()
            
            # 2. Connexions
            mock_db.connect.assert_called_once()
            mock_scraper.setup_session.assert_called_once()
            
            # 3. Extraction
            mock_scraper.scrape_questions.assert_called_once_with(
                max_questions=10,
                tags=['python', 'javascript']
            )
            
            # 4. Stockage
            mock_db.store_questions.assert_called_once()
            stored_questions = mock_db.store_questions.call_args[0][0]
            assert len(stored_questions) == 5
            assert all(isinstance(q, QuestionData) for q in stored_questions)
            
            # 5. Analyse
            mock_analyzer.set_execution_metadata.assert_called_once()
            mock_analyzer.analyze_trends.assert_called_once()
            
            # 6. Sauvegarde
            mock_analyzer.save_results.assert_called_once()
            
            # 7. Nettoyage
            mock_scraper.close.assert_called_once()  # close() au lieu de cleanup()
            mock_db.disconnect.assert_called_once()
    
    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_complete_pipeline_api_mode(self, sample_realistic_questions):
        """Test complet du pipeline en mode API."""
        with patch('main.Config') as mock_config_class, \
             patch('main.DatabaseManager') as mock_db_class, \
             patch('main.StackOverflowScraper') as mock_scraper_class, \
             patch('main.DataAnalyzer') as mock_analyzer_class, \
             patch('pathlib.Path.mkdir'), \
             patch('builtins.open', mock_open()):
            
            # Configuration des mocks
            mock_config = MagicMock()
            mock_config_class.return_value = mock_config
            
            mock_db = AsyncMock()
            mock_db_class.return_value = mock_db
            mock_db.store_questions.return_value = {
                'questions_stored': 3,
                'authors_new': 2,
                'authors_updated': 1
            }
            
            mock_scraper = AsyncMock()
            mock_scraper_class.return_value = mock_scraper
            # En mode API, on utilise fetch_via_api
            mock_scraper.fetch_via_api.return_value = sample_realistic_questions[:3]
            
            mock_analyzer = AsyncMock()
            mock_analyzer_class.return_value = mock_analyzer
            mock_analyzer.analyze_trends.return_value = {'api_mode': 'results'}
            
            # Exécution en mode API
            await main(
                max_questions=100,
                tags=['python'],
                use_api=True,
                analyze_data=True,
                storage_mode='append-only',
                analysis_scope='new-only'
            )
            
            # Vérifications spécifiques au mode API
            mock_scraper.fetch_via_api.assert_called_once_with(
                max_questions=100,
                tags=['python']
            )
            # scrape_questions ne doit PAS être appelé en mode API
            mock_scraper.scrape_questions.assert_not_called()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pipeline_append_only_mode(self, sample_realistic_questions):
        """Test du pipeline en mode append-only avec filtrage des doublons."""
        with patch('main.Config') as mock_config_class, \
             patch('main.DatabaseManager') as mock_db_class, \
             patch('main.StackOverflowScraper') as mock_scraper_class, \
             patch('main.DataAnalyzer') as mock_analyzer_class, \
             patch('main.store_questions_append_only') as mock_append_only:
            
            # Configuration des mocks
            mock_config = MagicMock()
            mock_config_class.return_value = mock_config
            
            mock_db = AsyncMock()
            mock_db_class.return_value = mock_db
            
            mock_scraper = AsyncMock()
            mock_scraper_class.return_value = mock_scraper
            mock_scraper.scrape_questions.return_value = sample_realistic_questions
            
            mock_analyzer = AsyncMock()
            mock_analyzer_class.return_value = mock_analyzer
            
            # Mock pour mode append-only (simule filtrage des doublons)
            mock_append_only.return_value = {
                'questions_stored': 2,  # Seulement 2 nouvelles sur 5
                'authors_new': 1,
                'authors_updated': 1
            }
            
            # Exécution en mode append-only
            await main(
                max_questions=50,
                use_api=False,
                storage_mode='append-only',
                analysis_scope='new-only'
            )
            
            # Vérifications du mode append-only
            mock_append_only.assert_called_once()
            # store_questions standard ne doit PAS être appelé
            mock_db.store_questions.assert_not_called()
            
            # L'analyse doit être appelée avec les nouvelles questions seulement
            mock_analyzer.analyze_trends.assert_called_once()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pipeline_no_analysis_mode(self, sample_realistic_questions):
        """Test du pipeline avec analyse désactivée."""
        with patch('main.Config') as mock_config_class, \
             patch('main.DatabaseManager') as mock_db_class, \
             patch('main.StackOverflowScraper') as mock_scraper_class, \
             patch('main.DataAnalyzer') as mock_analyzer_class:
            
            # Configuration des mocks
            mock_config = MagicMock()
            mock_config_class.return_value = mock_config
            
            mock_db = AsyncMock()
            mock_db_class.return_value = mock_db
            mock_db.store_questions.return_value = {
                'questions_stored': 5,
                'authors_new': 3,
                'authors_updated': 2
            }
            
            mock_scraper = AsyncMock()
            mock_scraper_class.return_value = mock_scraper
            mock_scraper.scrape_questions.return_value = sample_realistic_questions
            
            mock_analyzer = AsyncMock()
            mock_analyzer_class.return_value = mock_analyzer
            
            # Exécution sans analyse
            await main(
                max_questions=20,
                analyze_data=False  # Analyse désactivée
            )
            
            # Vérifications - analyse désactivée
            mock_analyzer.analyze_trends.assert_not_called()
            # Mais un rapport d'exécution doit quand même être généré
            mock_analyzer.save_results.assert_called_once()
            
            # Vérifier que le résultat indique l'analyse désactivée
            save_call = mock_analyzer.save_results.call_args[0][0]
            assert save_call.get('analysis_disabled') is True
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pipeline_analysis_scope_new_only_no_new_questions(self, sample_realistic_questions):
        """Test de l'annulation intelligente de l'analyse quand aucune nouvelle question."""
        with patch('main.Config') as mock_config_class, \
             patch('main.DatabaseManager') as mock_db_class, \
             patch('main.StackOverflowScraper') as mock_scraper_class, \
             patch('main.DataAnalyzer') as mock_analyzer_class:
            
            # Configuration des mocks
            mock_config = MagicMock()
            mock_config_class.return_value = mock_config
            
            mock_db = AsyncMock()
            mock_db_class.return_value = mock_db
            # Simulation : aucune nouvelle question stockée (toutes sont des doublons)
            mock_db.store_questions.return_value = {
                'questions_stored': 0,
                'authors_new': 0,
                'authors_updated': 0
            }
            
            # Mock de get_question_ids pour simuler que toutes les questions existent déjà
            existing_ids = [q.question_id for q in sample_realistic_questions]
            mock_db.get_question_ids.return_value = existing_ids
            
            mock_scraper = AsyncMock()
            mock_scraper_class.return_value = mock_scraper
            mock_scraper.scrape_questions.return_value = sample_realistic_questions
            
            mock_analyzer = AsyncMock()
            mock_analyzer_class.return_value = mock_analyzer
            
            # Mock de store_questions_append_only
            with patch('main.store_questions_append_only') as mock_append_only:
                mock_append_only.return_value = {
                    'questions_stored': 0,  # Aucune nouvelle question
                    'authors_new': 0,
                    'authors_updated': 0
                }
                
                # Exécution avec analysis_scope='new-only' et storage_mode='append-only'
                await main(
                    max_questions=30,
                    analysis_scope='new-only',  # Analyse seulement les nouvelles
                    storage_mode='append-only'  # Important pour la logique new_questions_ids
                )
            
            # Vérifications - analyse annulée intelligemment
            mock_analyzer.analyze_trends.assert_not_called()
            mock_analyzer.save_results.assert_called_once()
            
            # Vérifier que le résultat indique l'annulation
            save_call = mock_analyzer.save_results.call_args[0][0]
            # L'information d'annulation est dans execution_info
            execution_info = save_call.get('execution_info', {})
            assert execution_info.get('analysis_status') == '⚠️ Annulée - Aucune nouvelle question'
    
    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_pipeline_with_realistic_errors(self, sample_realistic_questions):
        """Test du pipeline avec gestion d'erreurs réalistes."""
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
            # Simulation d'une erreur lors du scraping
            mock_scraper.scrape_questions.side_effect = Exception("Network timeout")
            
            mock_analyzer = AsyncMock()
            mock_analyzer_class.return_value = mock_analyzer
            
            # Exécution - doit lever l'exception mais nettoyer proprement
            with pytest.raises(Exception, match="Network timeout"):
                await main(max_questions=10)
            
            # Vérifications du nettoyage même en cas d'erreur
            mock_scraper.close.assert_called_once()  # close() au lieu de cleanup()
            mock_db.disconnect.assert_called_once()
    
    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_pipeline_performance_metrics(self, sample_realistic_questions):
        """Test des métriques de performance du pipeline."""
        with patch('main.Config') as mock_config_class, \
             patch('main.DatabaseManager') as mock_db_class, \
             patch('main.StackOverflowScraper') as mock_scraper_class, \
             patch('main.DataAnalyzer') as mock_analyzer_class:
            
            # Configuration des mocks avec délais simulés
            mock_config = MagicMock()
            mock_config_class.return_value = mock_config
            
            mock_db = AsyncMock()
            mock_db_class.return_value = mock_db
            mock_db.store_questions.return_value = {
                'questions_stored': 5,
                'authors_new': 3,
                'authors_updated': 2
            }
            
            mock_scraper = AsyncMock()
            mock_scraper_class.return_value = mock_scraper
            
            # Simulation d'un délai d'extraction
            async def slow_scraping(*args, **kwargs):
                await asyncio.sleep(0.1)  # Petit délai pour simulation
                return sample_realistic_questions
            
            mock_scraper.scrape_questions.side_effect = slow_scraping
            
            mock_analyzer = AsyncMock()
            mock_analyzer_class.return_value = mock_analyzer
            
            # Simulation d'un délai d'analyse
            async def slow_analysis(*args, **kwargs):
                await asyncio.sleep(0.05)
                return {'performance': 'test'}
            
            mock_analyzer.analyze_trends.side_effect = slow_analysis
            
            # Mesure du temps d'exécution
            start_time = datetime.now()
            
            await main(
                max_questions=15,
                use_api=False,
                analyze_data=True
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Vérifications de performance
            assert execution_time < 10.0, "Le pipeline ne doit pas prendre plus de 10 secondes"
            
            # Vérifier que les métadonnées d'exécution sont passées à l'analyseur
            mock_analyzer.set_execution_metadata.assert_called_once()
            
            # Récupérer les métadonnées d'exécution
            execution_metadata = mock_analyzer.set_execution_metadata.call_args[0][0]
            
            # Vérifications des métriques
            assert 'scraping_duration' in execution_metadata
            assert 'questions_extracted' in execution_metadata
            assert 'extraction_rate' in execution_metadata
            assert execution_metadata['questions_extracted'] == 5
            assert execution_metadata['extraction_rate'] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
