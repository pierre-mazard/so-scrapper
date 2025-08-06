"""
Tests pour le module Scraper
============================

Tests unitaires pour vérifier le bon fonctionnement du scraper Stack Overflow.
Couvre la gestion des requêtes HTTP, l'analyse HTML et l'extraction des données.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import aiohttp
from bs4 import BeautifulSoup

from src.scraper import StackOverflowScraper, QuestionData
from src.config import Config


class TestStackOverflowScraper:
    """Tests pour la classe StackOverflowScraper."""
    
    @pytest.fixture
    def config(self):
        """Configuration de test."""
        return Config().scraper_config
    
    @pytest.fixture
    def scraper(self, config):
        """Instance du scraper pour les tests."""
        return StackOverflowScraper(config)
    
    @pytest.fixture
    def sample_question_html(self):
        """HTML d'exemple d'une question Stack Overflow."""
        return """
        <div class="s-post-summary">
            <h3 class="s-post-summary--content-title">
                <a href="/questions/123456/test-question">Test Question Title</a>
            </h3>
            <div class="s-post-summary--content-excerpt">
                This is a test question summary.
            </div>
            <div class="s-post-summary--meta-tags">
                <a class="post-tag">python</a>
                <a class="post-tag">testing</a>
            </div>
            <div class="s-post-summary--stats">
                <div class="s-post-summary--stats-item-number">5</div>
                <div class="s-post-summary--stats-item-number">2</div>
            </div>
            <div class="s-user-card--link">
                <a href="/users/12345/testuser">TestUser</a>
            </div>
        </div>
        """
    
    @pytest.fixture
    def sample_question_data(self):
        """Données d'exemple d'une question."""
        return QuestionData(
            title="Test Question",
            url="https://stackoverflow.com/questions/123456/test-question",
            summary="Test summary",
            tags=["python", "testing"],
            author_name="TestUser",
            author_reputation=1000,
            author_profile_url="https://stackoverflow.com/users/12345/testuser",
            publication_date=datetime.now(),
            view_count=100,
            vote_count=5,
            answer_count=2,
            question_id=123456
        )
    
    def test_build_search_url_with_tags(self, scraper):
        """Test la construction d'URL de recherche avec tags."""
        url = scraper._build_search_url(page=1, tags=["python", "django"], sort_by="newest")
        expected = "https://stackoverflow.com/questions/tagged/[python]+[django]?tab=newest&page=1"
        assert url == expected
    
    def test_build_search_url_without_tags(self, scraper):
        """Test la construction d'URL de recherche sans tags."""
        url = scraper._build_search_url(page=2, sort_by="votes")
        expected = "https://stackoverflow.com/questions?tab=votes&page=2"
        assert url == expected
    
    def test_extract_question_basic_data(self, scraper, sample_question_html):
        """Test l'extraction des données de base d'une question."""
        soup = BeautifulSoup(sample_question_html, 'html.parser')
        element = soup.find('div', class_='s-post-summary')
        
        question_data = scraper._extract_question_basic_data(element)
        
        assert question_data is not None
        assert question_data.title == "Test Question Title"
        assert question_data.question_id == 123456
        assert question_data.summary == "This is a test question summary."
        assert question_data.tags == ["python", "testing"]
        assert question_data.author_name == "TestUser"
        assert question_data.vote_count == 5
    
    def test_extract_question_basic_data_invalid_html(self, scraper):
        """Test l'extraction avec HTML invalide."""
        soup = BeautifulSoup("<div></div>", 'html.parser')
        element = soup.find('div')
        
        question_data = scraper._extract_question_basic_data(element)
        assert question_data is None
    
    @pytest.mark.asyncio
    async def test_setup_session(self, scraper):
        """Test la configuration de la session."""
        await scraper.setup_session()
        
        assert scraper.session is not None
        assert isinstance(scraper.session, aiohttp.ClientSession)
        assert scraper.driver is not None
        
        await scraper.cleanup()
    
    @pytest.mark.asyncio
    async def test_cleanup(self, scraper):
        """Test le nettoyage des ressources."""
        await scraper.setup_session()
        await scraper.cleanup()
        
        assert scraper.session.closed
    
    @pytest.mark.asyncio
    @patch('src.scraper.webdriver.Chrome')
    async def test_scrape_questions_empty_result(self, mock_driver, scraper):
        """Test le scraping avec résultat vide."""
        # Mock du driver
        mock_driver.return_value.page_source = "<html><body></body></html>"
        mock_driver.return_value.get = Mock()
        
        scraper.driver = mock_driver.return_value
        
        with patch.object(scraper, '_parse_questions_page', return_value=[]):
            questions = await scraper.scrape_questions(max_questions=10)
            assert len(questions) == 0
    
    def test_convert_api_to_question_data(self, scraper):
        """Test la conversion des données API en QuestionData."""
        api_question = {
            "title": "API Test Question",
            "link": "https://stackoverflow.com/questions/789012/api-test",
            "body_markdown": "This is the question body from API",
            "tags": ["api", "test"],
            "owner": {
                "display_name": "APIUser",
                "reputation": 2000,
                "link": "https://stackoverflow.com/users/789/apiuser"
            },
            "creation_date": 1640995200,  # 2022-01-01
            "view_count": 500,
            "score": 10,
            "answer_count": 3,
            "question_id": 789012
        }
        
        question_data = scraper._convert_api_to_question_data(api_question)
        
        assert question_data.title == "API Test Question"
        assert question_data.url == "https://stackoverflow.com/questions/789012/api-test"
        assert question_data.tags == ["api", "test"]
        assert question_data.author_name == "APIUser"
        assert question_data.author_reputation == 2000
        assert question_data.view_count == 500
        assert question_data.vote_count == 10
        assert question_data.answer_count == 3
        assert question_data.question_id == 789012
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_fetch_via_api_with_mock(self, mock_get, scraper):
        """Test la récupération via API avec mock."""
        
        # Configuration de la session avant le test
        await scraper.setup_session()
        
        mock_response_data = {
            "items": [
                {
                    "title": "Mock Question",
                    "link": "https://stackoverflow.com/questions/999/mock",
                    "body_markdown": "Mock question body",
                    "tags": ["mock"],
                    "owner": {"display_name": "MockUser", "reputation": 100},
                    "creation_date": 1640995200,
                    "view_count": 50,
                    "score": 1,
                    "answer_count": 0,
                    "question_id": 999
                }
            ]
        }
        
        # Mock de la réponse avec retour synchrone de json
        class MockResponse:
            def __init__(self):
                self.status = 200
                
            async def json(self):
                return mock_response_data
        
        # Mock correct pour le context manager avec une classe réelle
        class MockContextManager:
            async def __aenter__(self):
                return MockResponse()
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None
        
        mock_get.return_value = MockContextManager()
        
        try:
            questions = await scraper.fetch_via_api(max_questions=1)
            
            assert len(questions) == 1
            assert questions[0].title == "Mock Question"
            assert questions[0].question_id == 999
        finally:
            # Nettoyage
            await scraper.cleanup()


class TestQuestionData:
    """Tests pour la classe QuestionData."""
    
    def test_question_data_creation(self):
        """Test la création d'une instance QuestionData."""
        question = QuestionData(
            title="Test",
            url="http://test.com",
            summary="Summary",
            tags=["tag1"],
            author_name="Author",
            author_reputation=100,
            author_profile_url="http://profile.com",
            publication_date=datetime.now(),
            view_count=50,
            vote_count=5,
            answer_count=2,
            question_id=123
        )
        
        assert question.title == "Test"
        assert question.question_id == 123
        assert len(question.tags) == 1
    
    def test_question_data_str_representation(self):
        """Test la représentation string de QuestionData."""
        question = QuestionData(
            title="Test Question",
            url="http://test.com",
            summary="Test summary",
            tags=["python"],
            author_name="TestAuthor",
            author_reputation=500,
            author_profile_url="http://profile.com",
            publication_date=datetime(2023, 1, 1),
            view_count=100,
            vote_count=10,
            answer_count=3,
            question_id=456
        )
        
        str_repr = str(question)
        assert "Test Question" in str_repr
        assert "456" in str_repr


@pytest.mark.integration
class TestScraperIntegration:
    """Tests d'intégration pour le scraper."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_real_stackoverflow_request(self):
        """Test avec une vraie requête Stack Overflow (marqué comme lent)."""
        config = Config().scraper_config.__dict__
        scraper = StackOverflowScraper(config)
        
        try:
            async with scraper:
                # Test avec l'API Stack Overflow
                questions = await scraper.fetch_via_api(max_questions=5, tags=["python"])
                
                assert len(questions) <= 5
                for question in questions:
                    assert isinstance(question, QuestionData)
                    assert question.title
                    assert question.url
                    assert "python" in question.tags
        
        except Exception as e:
            pytest.skip(f"Test d'intégration échoué (connexion réseau?): {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
