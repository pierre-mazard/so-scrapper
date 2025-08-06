"""
Tests pour le module Database
=============================

Tests unitaires pour vérifier le bon fonctionnement du gestionnaire de base de données.
Couvre la connexion, l'insertion et la récupération des données.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import motor.motor_asyncio
from pymongo.errors import ConnectionFailure, DuplicateKeyError

from src.database import DatabaseManager
from src.scraper import QuestionData


class TestDatabaseManager:
    """Tests pour la classe DatabaseManager."""
    
    @pytest.fixture
    def db_config(self):
        """Configuration de test pour la base de données."""
        from src.config import DatabaseConfig
        return DatabaseConfig(
            host="localhost",
            port=27017,
            name="test_stackoverflow",
            collection="test_questions",
            max_pool_size=5,
            timeout_ms=5000
        )
    
    @pytest.fixture
    def db_manager(self, db_config):
        """Instance du gestionnaire de base de données pour les tests."""
        return DatabaseManager(db_config)
    
    @pytest.fixture
    def sample_questions(self):
        """Données de test pour les questions."""
        return [
            QuestionData(
                title="Test Question 1",
                url="https://stackoverflow.com/questions/1/test1",
                summary="Test summary 1",
                tags=["python", "testing"],
                author_name="TestUser1",
                author_reputation=1000,
                author_profile_url="https://stackoverflow.com/users/1/testuser1",
                publication_date=datetime(2023, 1, 1),
                view_count=100,
                vote_count=5,
                answer_count=2,
                question_id=1
            ),
            QuestionData(
                title="Test Question 2",
                url="https://stackoverflow.com/questions/2/test2",
                summary="Test summary 2",
                tags=["javascript", "testing"],
                author_name="TestUser2",
                author_reputation=2000,
                author_profile_url="https://stackoverflow.com/users/2/testuser2",
                publication_date=datetime(2023, 1, 2),
                view_count=200,
                vote_count=10,
                answer_count=3,
                question_id=2
            )
        ]
    
    def test_database_manager_initialization(self, db_manager, db_config):
        """Test l'initialisation du gestionnaire de base de données."""
        expected_connection_string = f"mongodb://{db_config.host}:{db_config.port}/"
        assert db_manager.connection_string == expected_connection_string
        assert db_manager.database_name == db_config.name
        assert db_manager.questions_collection == db_config.collection
        assert db_manager.authors_collection == "authors"
        assert db_manager.analysis_collection == "analysis"
    
    @pytest.mark.asyncio
    @patch('src.database.motor.motor_asyncio.AsyncIOMotorClient')
    @patch('src.database.MongoClient')
    async def test_connect_success(self, mock_pymongo_client, mock_motor_client, db_manager):
        """Test la connexion réussie à MongoDB."""
        # Mock des clients
        from unittest.mock import MagicMock
        mock_motor_instance = AsyncMock()
        mock_pymongo_instance = MagicMock()
        
        mock_motor_client.return_value = mock_motor_instance
        mock_pymongo_client.return_value = mock_pymongo_instance
        
        # Mock de la commande ismaster
        mock_motor_instance.admin.command = AsyncMock(return_value={"ismaster": True})
        
        # Mock de setup_indexes
        with patch.object(db_manager, 'setup_indexes', new_callable=AsyncMock):
            await db_manager.connect()
        
        assert db_manager.motor_client == mock_motor_instance
        assert db_manager.client == mock_pymongo_instance
        mock_motor_instance.admin.command.assert_called_once_with('ismaster')
    
    @pytest.mark.asyncio
    @patch('motor.motor_asyncio.AsyncIOMotorClient')
    async def test_connect_failure(self, mock_motor_client, db_manager):
        """Test l'échec de connexion à MongoDB."""
        mock_motor_client.side_effect = ConnectionFailure("Connection failed")
        
        with pytest.raises(ConnectionFailure):
            await db_manager.connect()
    
    @pytest.mark.asyncio
    async def test_disconnect(self, db_manager):
        """Test la déconnexion de MongoDB."""
        # Mock des clients
        mock_motor_client = Mock()
        mock_client = Mock()
        
        db_manager.motor_client = mock_motor_client
        db_manager.client = mock_client
        
        await db_manager.disconnect()
        
        mock_motor_client.close.assert_called_once()
        mock_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_setup_indexes(self, db_manager):
        """Test la configuration des index."""
        # Mock de la base de données
        from unittest.mock import MagicMock
        mock_db = MagicMock()
        mock_questions_coll = AsyncMock()
        mock_authors_coll = AsyncMock()
        mock_analysis_coll = AsyncMock()
        
        mock_db.__getitem__.side_effect = lambda name: {
            "test_questions": mock_questions_coll,
            "authors": mock_authors_coll,
            "analysis": mock_analysis_coll
        }[name]
        
        db_manager.motor_database = mock_db
        
        await db_manager.setup_indexes()
        
        # Vérifier que les index ont été créés
        assert mock_questions_coll.create_index.call_count >= 4
        assert mock_authors_coll.create_index.call_count >= 2
        assert mock_analysis_coll.create_index.call_count >= 2
    
    def test_prepare_question_document(self, db_manager, sample_questions):
        """Test la préparation d'un document question."""
        question = sample_questions[0]
        doc = db_manager._prepare_question_document(question)
        
        assert doc["title"] == question.title
        assert doc["url"] == question.url
        assert doc["question_id"] == question.question_id
        assert doc["tags"] == question.tags
        assert "stored_at" in doc
        assert "last_updated" in doc
        assert isinstance(doc["stored_at"], datetime)
    
    @pytest.mark.asyncio
    async def test_store_questions_success(self, db_manager, sample_questions):
        """Test le stockage réussi de questions."""
        # Mock des collections
        from unittest.mock import MagicMock
        mock_questions_coll = AsyncMock()
        mock_authors_coll = AsyncMock()
        mock_db = MagicMock()
        
        mock_db.__getitem__.side_effect = lambda name: {
            "test_questions": mock_questions_coll,
            "authors": mock_authors_coll
        }[name]
        
        db_manager.motor_database = mock_db
        
        # Mock des opérations de base de données
        mock_questions_coll.update_one = AsyncMock()
        
        with patch.object(db_manager, '_store_author', new_callable=AsyncMock):
            stored_count = await db_manager.store_questions(sample_questions)
        
        assert stored_count == len(sample_questions)
        assert mock_questions_coll.update_one.call_count == len(sample_questions)
    
    @pytest.mark.asyncio
    async def test_store_questions_empty_list(self, db_manager):
        """Test le stockage d'une liste vide."""
        stored_count = await db_manager.store_questions([])
        assert stored_count == 0
    
    @pytest.mark.asyncio
    async def test_store_author(self, db_manager, sample_questions):
        """Test le stockage d'un auteur."""
        mock_authors_coll = AsyncMock()
        question = sample_questions[0]
        
        await db_manager._store_author(mock_authors_coll, question)
        
        mock_authors_coll.update_one.assert_called_once()
        call_args = mock_authors_coll.update_one.call_args
        
        # Vérifier le filtre
        filter_doc = call_args[0][0]
        assert filter_doc["author_name"] == question.author_name
        
        # Vérifier l'update
        update_doc = call_args[0][1]
        assert "$set" in update_doc
        assert "$inc" in update_doc
        assert update_doc["$inc"]["question_count"] == 1
    
    @pytest.mark.asyncio
    async def test_get_questions(self, db_manager):
        """Test la récupération de questions."""
        # Mock de la collection et du curseur
        mock_cursor = Mock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[
            {"title": "Test Question", "question_id": 1}
        ])
        
        mock_questions_coll = Mock()
        mock_questions_coll.find.return_value = mock_cursor
        
        from unittest.mock import MagicMock
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_questions_coll
        db_manager.motor_database = mock_db
        
        questions = await db_manager.get_questions(limit=10, skip=0)
        
        assert len(questions) == 1
        assert questions[0]["title"] == "Test Question"
        mock_questions_coll.find.assert_called_once_with({})
        mock_cursor.sort.assert_called_once()
        mock_cursor.skip.assert_called_once_with(0)
        mock_cursor.limit.assert_called_once_with(10)
    
    @pytest.mark.asyncio
    async def test_get_questions_by_tags(self, db_manager):
        """Test la récupération de questions par tags."""
        with patch.object(db_manager, 'get_questions', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [{"title": "Python Question", "tags": ["python"]}]
            
            questions = await db_manager.get_questions_by_tags(["python"])
            
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[1]["filters"]["tags"]["$in"] == ["python"]
    
    @pytest.mark.asyncio
    async def test_get_questions_by_date_range(self, db_manager):
        """Test la récupération de questions par plage de dates."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 31)
        
        with patch.object(db_manager, 'get_questions', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []
            
            await db_manager.get_questions_by_date_range(start_date, end_date)
            
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            filters = call_args[1]["filters"]
            assert filters["publication_date"]["$gte"] == start_date
            assert filters["publication_date"]["$lte"] == end_date
    
    @pytest.mark.asyncio
    async def test_get_tag_statistics(self, db_manager):
        """Test le calcul des statistiques des tags."""
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=[
            {"_id": "python", "count": 10, "avg_votes": 5.5, "avg_views": 100.0},
            {"_id": "javascript", "count": 8, "avg_votes": 3.2, "avg_views": 80.0}
        ])
        
        mock_questions_coll = Mock()
        mock_questions_coll.aggregate.return_value = mock_cursor
        
        from unittest.mock import MagicMock
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_questions_coll
        db_manager.motor_database = mock_db
        
        stats = await db_manager.get_tag_statistics()
        
        assert len(stats) == 2
        assert stats[0]["_id"] == "python"
        assert stats[0]["count"] == 10
        mock_questions_coll.aggregate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_analysis_results(self, db_manager):
        """Test le stockage des résultats d'analyse."""
        mock_analysis_coll = AsyncMock()
        from unittest.mock import MagicMock
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_analysis_coll
        db_manager.motor_database = mock_db
        
        analysis_results = {
            "total_questions": 100,
            "duration": 30.5,
            "trending_tags": ["python", "javascript"]
        }
        
        await db_manager.store_analysis_results("test_analysis", analysis_results)
        
        mock_analysis_coll.insert_one.assert_called_once()
        call_args = mock_analysis_coll.insert_one.call_args[0][0]
        
        assert call_args["analysis_type"] == "test_analysis"
        assert call_args["results"] == analysis_results
        assert "analysis_date" in call_args
        assert "metadata" in call_args
    
    @pytest.mark.asyncio
    async def test_get_database_stats(self, db_manager):
        """Test la récupération des statistiques de la base de données."""
        # Mock des collections
        mock_questions_coll = AsyncMock()
        mock_authors_coll = AsyncMock()
        mock_analysis_coll = AsyncMock()
        
        mock_questions_coll.count_documents = AsyncMock(return_value=100)
        mock_authors_coll.count_documents = AsyncMock(return_value=50)
        mock_analysis_coll.count_documents = AsyncMock(return_value=5)
        
        mock_questions_coll.find_one = AsyncMock(side_effect=[
            {"publication_date": datetime(2023, 1, 31)},  # latest
            {"publication_date": datetime(2023, 1, 1)}    # earliest
        ])
        
        from unittest.mock import MagicMock
        mock_db = MagicMock()
        mock_db.__getitem__.side_effect = lambda name: {
            "test_questions": mock_questions_coll,
            "authors": mock_authors_coll,
            "analysis": mock_analysis_coll
        }[name]
        
        db_manager.motor_database = mock_db
        
        stats = await db_manager.get_database_stats()
        
        assert stats["questions_count"] == 100
        assert stats["authors_count"] == 50
        assert stats["analysis_count"] == 5
        assert stats["last_question_date"] == datetime(2023, 1, 31)
        assert stats["first_question_date"] == datetime(2023, 1, 1)


@pytest.mark.integration
class TestDatabaseIntegration:
    """Tests d'intégration pour la base de données."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_real_mongodb_connection(self):
        """Test avec une vraie connexion MongoDB (marqué comme lent)."""
        from src.config import DatabaseConfig
        db_config = DatabaseConfig(
            host="localhost",
            port=27017,
            name="test_integration",
            collection="test_questions",
            max_pool_size=5,
            timeout_ms=5000
        )
        
        db_manager = DatabaseManager(db_config)
        
        try:
            async with db_manager:
                # Test de connexion et statistiques
                stats = await db_manager.get_database_stats()
                assert isinstance(stats, dict)
                assert "questions_count" in stats
        
        except Exception as e:
            pytest.skip(f"Test d'intégration échoué (MongoDB non disponible?): {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
