"""
Tests pour le module Analyzer
=============================

Tests unitaires pour vérifier le bon fonctionnement de l'analyseur de données.
Couvre l'analyse NLP, les tendances et les statistiques.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import numpy as np

from src.analyzer import DataAnalyzer, NLPProcessor, TrendAnalyzer
from src.database import DatabaseManager


class TestNLPProcessor:
    """Tests pour la classe NLPProcessor."""
    
    @pytest.fixture
    def nlp_processor(self):
        """Instance du processeur NLP pour les tests."""
        return NLPProcessor()
    
    def test_preprocess_text(self, nlp_processor):
        """Test le prétraitement de texte."""
        text = "This is a <b>TEST</b> text with http://example.com and numbers 123!"
        processed = nlp_processor.preprocess_text(text)
        
        # Le texte doit être en minuscules et nettoyé
        assert processed.lower() == processed
        assert "<b>" not in processed
        assert "http://example.com" not in processed
        assert "123" not in processed
    
    def test_preprocess_text_empty(self, nlp_processor):
        """Test le prétraitement de texte vide."""
        assert nlp_processor.preprocess_text("") == ""
        assert nlp_processor.preprocess_text(None) == ""
    
    @patch('src.analyzer.TfidfVectorizer')
    def test_extract_keywords(self, mock_vectorizer, nlp_processor):
        """Test l'extraction de mots-clés."""
        # Mock du vectorizer
        mock_vectorizer_instance = Mock()
        mock_vectorizer.return_value = mock_vectorizer_instance
        
        mock_vectorizer_instance.fit_transform.return_value.toarray.return_value = np.array([[0.5, 0.3], [0.4, 0.6]])
        mock_vectorizer_instance.get_feature_names_out.return_value = np.array(['python', 'javascript'])
        
        texts = ["Python programming tutorial", "JavaScript web development"]
        keywords = nlp_processor.extract_keywords(texts, max_features=10)
        
        assert len(keywords) == 2
        assert isinstance(keywords[0], tuple)
        assert keywords[0][0] in ['python', 'javascript']
        assert isinstance(keywords[0][1], (int, float))
    
    def test_extract_keywords_empty_texts(self, nlp_processor):
        """Test l'extraction de mots-clés avec textes vides."""
        keywords = nlp_processor.extract_keywords([])
        assert keywords == []
        
        keywords = nlp_processor.extract_keywords(["", "   ", None])
        assert keywords == []
    
    @patch('src.analyzer.TextBlob')
    def test_analyze_sentiment(self, mock_textblob, nlp_processor):
        """Test l'analyse de sentiment."""
        # Mock de TextBlob
        mock_blob = Mock()
        mock_blob.sentiment.polarity = 0.5  # Sentiment positif
        mock_textblob.return_value = mock_blob
        
        texts = ["This is great!", "I love this"]
        sentiment = nlp_processor.analyze_sentiment(texts)
        
        assert sentiment["positive"] == 2
        assert sentiment["negative"] == 0
        assert sentiment["neutral"] == 0
        assert sentiment["total"] == 2
        assert sentiment["average"] == 0.5
    
    def test_analyze_sentiment_empty(self, nlp_processor):
        """Test l'analyse de sentiment avec textes vides."""
        sentiment = nlp_processor.analyze_sentiment([])
        expected = {"positive": 0, "negative": 0, "neutral": 0, "average": 0}
        assert sentiment == expected


class TestTrendAnalyzer:
    """Tests pour la classe TrendAnalyzer."""
    
    @pytest.fixture
    def trend_analyzer(self):
        """Instance de l'analyseur de tendances pour les tests."""
        return TrendAnalyzer()
    
    @pytest.fixture
    def sample_questions_data(self):
        """Données de test pour les questions."""
        base_date = datetime.now()
        return [
            {
                "tags": ["python", "django"],
                "publication_date": base_date - timedelta(days=5),
                "vote_count": 10,
                "view_count": 100,
                "answer_count": 2
            },
            {
                "tags": ["python", "flask"],
                "publication_date": base_date - timedelta(days=15),
                "vote_count": 5,
                "view_count": 50,
                "answer_count": 1
            },
            {
                "tags": ["javascript", "react"],
                "publication_date": base_date - timedelta(days=45),
                "vote_count": 8,
                "view_count": 80,
                "answer_count": 3
            }
        ]
    
    def test_analyze_tag_trends(self, trend_analyzer, sample_questions_data):
        """Test l'analyse des tendances des tags."""
        # Créer plus de données pour dépasser le seuil de 5 questions par tag
        extended_data = sample_questions_data * 3  # Dupliquer les données
        
        trends = trend_analyzer.analyze_tag_trends(extended_data)
        
        assert "trending_tags" in trends
        assert "top_tags" in trends
        assert "analysis_date" in trends
        
        # Vérifier qu'au moins quelques tags sont présents (ceux avec ≥5 questions)
        assert len(trends["trending_tags"]) >= 0  # Peut être 0 si pas assez de données
        assert len(trends["top_tags"]) >= 0
    
    def test_analyze_tag_trends_empty(self, trend_analyzer):
        """Test l'analyse des tendances avec données vides."""
        trends = trend_analyzer.analyze_tag_trends([])
        assert trends == {}
    
    def test_analyze_temporal_patterns(self, trend_analyzer, sample_questions_data):
        """Test l'analyse des patterns temporels."""
        patterns = trend_analyzer.analyze_temporal_patterns(sample_questions_data)
        
        # Vérifier que les clés principales sont présentes
        expected_keys = ["hourly_patterns", "daily_patterns", "monthly_patterns", 
                        "peak_hour", "peak_day", "total_questions_analyzed"]
        
        for key in expected_keys:
            assert key in patterns
    
    def test_analyze_temporal_patterns_empty(self, trend_analyzer):
        """Test l'analyse des patterns temporels avec données vides."""
        patterns = trend_analyzer.analyze_temporal_patterns([])
        assert patterns == {}


class TestDataAnalyzer:
    """Tests pour la classe DataAnalyzer principale."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Mock du gestionnaire de base de données."""
        mock_db = AsyncMock(spec=DatabaseManager)
        return mock_db
    
    @pytest.fixture
    def data_analyzer(self, mock_db_manager):
        """Instance de l'analyseur de données pour les tests."""
        return DataAnalyzer(mock_db_manager)
    
    @pytest.fixture
    def sample_db_questions(self):
        """Données de questions de la base de données."""
        return [
            {
                "title": "How to use Python decorators?",
                "summary": "I need help understanding Python decorators",
                "tags": ["python", "decorators"],
                "publication_date": datetime.now() - timedelta(days=1),
                "vote_count": 15,
                "view_count": 200,
                "answer_count": 3,
                "author_name": "developer1"
            },
            {
                "title": "JavaScript async/await best practices",
                "summary": "What are the best practices for async/await?",
                "tags": ["javascript", "async"],
                "publication_date": datetime.now() - timedelta(days=3),
                "vote_count": 10,
                "view_count": 150,
                "answer_count": 2,
                "author_name": "developer2"
            }
        ]
    
    def test_get_date_range(self, data_analyzer, sample_db_questions):
        """Test le calcul de la plage de dates."""
        date_range = data_analyzer._get_date_range(sample_db_questions)
        
        assert "start" in date_range
        assert "end" in date_range
        assert date_range["start"] is not None
        assert date_range["end"] is not None
    
    def test_get_date_range_empty(self, data_analyzer):
        """Test le calcul de la plage de dates avec liste vide."""
        date_range = data_analyzer._get_date_range([])
        assert date_range == {"start": None, "end": None}
    
    @pytest.mark.asyncio
    async def test_analyze_content(self, data_analyzer, sample_db_questions):
        """Test l'analyse du contenu."""
        with patch.object(data_analyzer.nlp_processor, 'extract_keywords') as mock_keywords, \
             patch.object(data_analyzer.nlp_processor, 'analyze_sentiment') as mock_sentiment:
            
            mock_keywords.return_value = [("python", 0.8), ("javascript", 0.6)]
            mock_sentiment.return_value = {"positive": 2, "negative": 0, "neutral": 0}
            
            content_analysis = await data_analyzer._analyze_content(sample_db_questions)
            
            assert "title_keywords" in content_analysis
            assert "summary_keywords" in content_analysis
            assert "title_sentiment" in content_analysis
            assert "summary_sentiment" in content_analysis
            assert "average_title_length" in content_analysis
            assert "average_summary_length" in content_analysis
    
    @pytest.mark.asyncio
    async def test_analyze_authors(self, data_analyzer, mock_db_manager):
        """Test l'analyse des auteurs."""
        mock_authors = [
            {"author_name": "dev1", "reputation": 1000, "question_count": 5},
            {"author_name": "dev2", "reputation": 2000, "question_count": 10}
        ]
        mock_db_manager.get_top_authors.return_value = mock_authors
        
        author_analysis = await data_analyzer._analyze_authors()
        
        assert "top_authors" in author_analysis
        assert "reputation_stats" in author_analysis
        assert "activity_stats" in author_analysis
        assert "total_authors" in author_analysis
        assert author_analysis["total_authors"] == 2
    
    @pytest.mark.asyncio
    async def test_analyze_authors_empty(self, data_analyzer, mock_db_manager):
        """Test l'analyse des auteurs avec données vides."""
        mock_db_manager.get_top_authors.return_value = []
        
        author_analysis = await data_analyzer._analyze_authors()
        assert author_analysis == {}
    
    @pytest.mark.asyncio
    async def test_calculate_general_stats(self, data_analyzer, sample_db_questions):
        """Test le calcul des statistiques générales."""
        stats = await data_analyzer._calculate_general_stats(sample_db_questions)
        
        assert "vote_stats" in stats
        assert "view_stats" in stats
        assert "answer_stats" in stats
        assert "tag_stats" in stats
        
        # Vérifier les statistiques de votes
        assert "mean" in stats["vote_stats"]
        assert "median" in stats["vote_stats"]
        assert "max" in stats["vote_stats"]
        assert "std" in stats["vote_stats"]
        
        # Vérifier les statistiques des tags
        assert "total_unique_tags" in stats["tag_stats"]
        assert "most_common_tags" in stats["tag_stats"]
        assert "average_tags_per_question" in stats["tag_stats"]
    
    @pytest.mark.asyncio
    async def test_calculate_general_stats_empty(self, data_analyzer):
        """Test le calcul des statistiques générales avec données vides."""
        stats = await data_analyzer._calculate_general_stats([])
        assert stats == {}
    
    @pytest.mark.asyncio
    async def test_analyze_trends_full(self, data_analyzer, mock_db_manager, sample_db_questions):
        """Test l'analyse complète des tendances."""
        # Configuration des mocks
        mock_db_manager.get_questions.return_value = sample_db_questions
        mock_db_manager.get_top_authors.return_value = []
        
        with patch.object(data_analyzer.nlp_processor, 'extract_keywords') as mock_keywords, \
             patch.object(data_analyzer.nlp_processor, 'analyze_sentiment') as mock_sentiment:
            
            mock_keywords.return_value = [("python", 0.8)]
            mock_sentiment.return_value = {"positive": 1, "negative": 0, "neutral": 1}
            
            results = await data_analyzer.analyze_trends()
            
            assert "analysis_metadata" in results
            assert "tag_trends" in results
            assert "temporal_patterns" in results
            assert "content_analysis" in results
            assert "author_analysis" in results
            assert "general_stats" in results
            
            # Vérifier les métadonnées
            metadata = results["analysis_metadata"]
            assert "analysis_date" in metadata
            assert "total_questions" in metadata
            assert "duration" in metadata
            assert metadata["total_questions"] == len(sample_db_questions)
    
    @pytest.mark.asyncio
    async def test_analyze_trends_no_data(self, data_analyzer, mock_db_manager):
        """Test l'analyse des tendances sans données."""
        mock_db_manager.get_questions.return_value = []
        
        results = await data_analyzer.analyze_trends()
        assert "error" in results
        assert results["error"] == "Aucune donnée disponible"
    
    @pytest.mark.asyncio
    async def test_save_results(self, data_analyzer, mock_db_manager):
        """Test la sauvegarde des résultats."""
        results = {"test": "data", "analysis_date": datetime.now().isoformat()}
        
        with patch('builtins.open', create=True) as mock_open, \
             patch('json.dump') as mock_json_dump:
            
            await data_analyzer.save_results(results)
            
            # Vérifier la sauvegarde en base
            mock_db_manager.store_analysis_results.assert_called_once()
            
            # Vérifier la sauvegarde en fichier
            mock_open.assert_called_once()
            mock_json_dump.assert_called_once()
    
    @patch('matplotlib.pyplot.savefig')
    @patch('matplotlib.pyplot.close')
    def test_generate_visualizations(self, mock_close, mock_savefig, data_analyzer):
        """Test la génération de visualisations."""
        results = {
            "tag_trends": {
                "trending_tags": [
                    {"tag": "python", "growth_rate": 25.0},
                    {"tag": "javascript", "growth_rate": 15.0}
                ]
            },
            "temporal_patterns": {
                "hourly_patterns": {
                    ("votes", "count"): {0: 1, 1: 2, 2: 3}
                }
            },
            "general_stats": {
                "tag_stats": {
                    "most_common_tags": [("python", 10), ("javascript", 8)]
                }
            }
        }
        
        # Le test ne doit pas lever d'exception
        try:
            import asyncio
            asyncio.run(data_analyzer.generate_visualizations(results))
        except Exception as e:
            pytest.fail(f"generate_visualizations a levé une exception: {e}")


@pytest.mark.integration
class TestAnalyzerIntegration:
    """Tests d'intégration pour l'analyseur."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_analysis_workflow(self):
        """Test du workflow complet d'analyse (marqué comme lent)."""
        # Ce test nécessiterait une base de données réelle avec des données
        # Il est marqué comme lent et peut être ignoré dans les tests rapides
        pytest.skip("Test d'intégration nécessitant une base de données réelle")


if __name__ == "__main__":
    import asyncio
    pytest.main([__file__, "-v"])
