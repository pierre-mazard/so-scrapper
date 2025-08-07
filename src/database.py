"""
Database Manager Module
======================

Module pour la gestion de la base de données non relationnelle.
Utilise MongoDB pour stocker les données extraites de Stack Overflow.

Classes:
    DatabaseManager: Gestionnaire principal de base de données
    MongoDBConnection: Connexion MongoDB avec gestion des erreurs
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import asdict

import motor.motor_asyncio
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError
import json

from .scraper import QuestionData


class DatabaseManager:
    """
    Gestionnaire de base de données pour le stockage des données Stack Overflow.
    
    Utilise MongoDB comme base de données non relationnelle pour stocker
    les questions, auteurs et analyses.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialise le gestionnaire de base de données.
        
        Args:
            config: Configuration de la base de données
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Configuration MongoDB
        self.connection_string = f"mongodb://{config.host}:{config.port}/"
        self.database_name = config.name
        
        # Collections  
        self.questions_collection = config.collection
        # Pour les autres collections, on utilise des noms par défaut
        self.authors_collection = "authors"
        self.analysis_collection = "analysis"
        
        # Clients
        self.client = None
        self.database = None
        self.motor_client = None
        self.motor_database = None
    
    async def __aenter__(self):
        """Context manager entry."""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.disconnect()
    
    async def connect(self) -> None:
        """Établit la connexion à MongoDB."""
        try:
            # Client Motor pour les opérations asynchrones
            self.motor_client = motor.motor_asyncio.AsyncIOMotorClient(
                self.connection_string,
                serverSelectionTimeoutMS=5000
            )
            self.motor_database = self.motor_client[self.database_name]
            
            # Client PyMongo pour les opérations synchrones
            self.client = MongoClient(
                self.connection_string,
                serverSelectionTimeoutMS=5000
            )
            self.database = self.client[self.database_name]
            
            # Test de connexion
            await self.motor_client.admin.command('ismaster')
            
            # Configuration des index
            await self.setup_indexes()
            
            self.logger.info("Connexion à MongoDB établie avec succès")
            
        except ConnectionFailure as e:
            self.logger.error(f"Erreur de connexion à MongoDB: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Erreur inattendue lors de la connexion: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Ferme la connexion à MongoDB."""
        if self.motor_client:
            self.motor_client.close()
        if self.client:
            self.client.close()
        self.logger.info("Connexion MongoDB fermée")
    
    async def setup_indexes(self) -> None:
        """Configure les index pour optimiser les performances."""
        try:
            # Index pour les questions
            questions_coll = self.motor_database[self.questions_collection]
            await questions_coll.create_index("question_id", unique=True)
            await questions_coll.create_index("publication_date")
            await questions_coll.create_index("tags")
            await questions_coll.create_index([("title", "text"), ("summary", "text")])
            
            # Index pour les auteurs
            authors_coll = self.motor_database[self.authors_collection]
            await authors_coll.create_index("author_name", unique=True)
            await authors_coll.create_index("reputation")
            
            # Index pour les analyses
            analysis_coll = self.motor_database[self.analysis_collection]
            await analysis_coll.create_index("analysis_date")
            await analysis_coll.create_index("analysis_type")
            
            self.logger.info("Index MongoDB configurés avec succès")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la configuration des index: {e}")
    
    async def store_questions(self, questions: List[QuestionData]) -> Dict[str, int]:
        """
        Stocke une liste de questions en base de données.
        
        Args:
            questions: Liste des questions à stocker
            
        Returns:
            Dict contenant les statistiques de stockage:
            - questions_stored: nombre de questions stockées
            - authors_new: nombre de nouveaux auteurs
            - authors_updated: nombre d'auteurs mis à jour
        """
        if not questions:
            self.logger.warning("Aucune question à stocker")
            return {'questions_stored': 0, 'authors_new': 0, 'authors_updated': 0}

        self.logger.info(f"[STORE] Début du stockage de {len(questions)} questions...")
        
        questions_coll = self.motor_database[self.questions_collection]
        authors_coll = self.motor_database[self.authors_collection]
        
        stored_count = 0
        authors_new = 0
        authors_updated = 0
        progress_interval = max(1, len(questions) // 10)  # Log tous les 10%
        
        for i, question in enumerate(questions, 1):
            try:
                # Log de progression
                if i % progress_interval == 0 or i == len(questions):
                    percentage = (i / len(questions)) * 100
                    self.logger.info(f"Questions extraites: Progression: {i}/{len(questions)} ({percentage:.1f}%)")
                
                # Préparation des données question
                question_doc = self._prepare_question_document(question)
                
                # Stockage de la question (avec upsert)
                await questions_coll.update_one(
                    {"question_id": question.question_id},
                    {"$set": question_doc},
                    upsert=True
                )
                
                # Stockage/mise à jour de l'auteur avec tracking
                author_status = await self._store_author(authors_coll, question)
                if author_status == 'new':
                    authors_new += 1
                elif author_status == 'updated':
                    authors_updated += 1
                
                stored_count += 1
                
            except DuplicateKeyError:
                self.logger.debug(f"Question {question.question_id} déjà existante")
            except Exception as e:
                self.logger.error(f"❌ Erreur lors du stockage de la question {question.question_id}: {e}")
        
        self.logger.info(f"[OK] Stockage terminé: {stored_count}/{len(questions)} questions sauvegardées")
        
        return {
            'questions_stored': stored_count,
            'authors_new': authors_new,
            'authors_updated': authors_updated
        }
    
    def _prepare_question_document(self, question: QuestionData) -> Dict[str, Any]:
        """Prépare un document MongoDB à partir d'une QuestionData."""
        doc = asdict(question)
        
        # Conversion de la date en format MongoDB
        if isinstance(doc['publication_date'], datetime):
            doc['publication_date'] = doc['publication_date']
        
        # Ajout de métadonnées
        doc['stored_at'] = datetime.utcnow()
        doc['last_updated'] = datetime.utcnow()
        
        return doc
    
    async def _store_author(self, authors_coll, question: QuestionData) -> str:
        """
        Stocke ou met à jour les informations d'un auteur.
        
        Returns:
            str: 'new' si nouvel auteur, 'updated' si mis à jour, 'skipped' si ignoré
        """
        if not question.author_name or question.author_name == "Unknown":
            return 'skipped'
        
        author_doc = {
            "author_name": question.author_name,
            "reputation": question.author_reputation,
            "profile_url": question.author_profile_url,
            "last_seen": datetime.utcnow(),
            "question_count": 1
        }
        
        # Upsert avec mise à jour des statistiques
        result = await authors_coll.update_one(
            {"author_name": question.author_name},
            {
                "$set": {
                    "reputation": question.author_reputation,
                    "profile_url": question.author_profile_url,
                    "last_seen": datetime.utcnow()
                },
                "$inc": {"question_count": 1},
                "$setOnInsert": {"first_seen": datetime.utcnow()}
            },
            upsert=True
        )
        
        # Déterminer si c'est un nouvel auteur ou une mise à jour
        if result.upserted_id:
            return 'new'
        else:
            return 'updated'
    
    async def get_questions(
        self,
        limit: Optional[int] = 100,
        skip: int = 0,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "publication_date"
    ) -> List[Dict[str, Any]]:
        """
        Récupère les questions de la base de données.
        
        Args:
            limit: Nombre maximum de questions à récupérer (None = toutes)
            skip: Nombre de questions à ignorer
            filters: Filtres à appliquer
            sort_by: Champ de tri
            
        Returns:
            Liste des questions
        """
        questions_coll = self.motor_database[self.questions_collection]
        
        query = filters or {}
        
        cursor = questions_coll.find(query).sort(sort_by, -1).skip(skip)
        
        if limit is not None:
            cursor = cursor.limit(limit)
            questions = await cursor.to_list(length=limit)
        else:
            questions = await cursor.to_list(length=None)
        
        return questions
    
    async def get_questions_by_ids(self, question_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Récupère les questions par leurs IDs.
        
        Args:
            question_ids: Liste des IDs des questions à récupérer
            
        Returns:
            Liste des questions correspondant aux IDs
        """
        if not question_ids:
            return []
            
        questions_coll = self.motor_database[self.questions_collection]
        
        # Utiliser $in pour récupérer toutes les questions avec les IDs spécifiés
        query = {"question_id": {"$in": question_ids}}
        
        cursor = questions_coll.find(query).sort("publication_date", -1)
        questions = await cursor.to_list(length=len(question_ids))
        
        return questions
    
    async def get_question_ids(self) -> List[int]:
        """
        Récupère tous les IDs des questions existantes dans la base.
        
        Returns:
            Liste des IDs des questions
        """
        questions_coll = self.motor_database[self.questions_collection]
        
        # Récupérer seulement le champ question_id de toutes les questions
        cursor = questions_coll.find({}, {"question_id": 1, "_id": 0})
        docs = await cursor.to_list(length=None)
        
        return [doc["question_id"] for doc in docs]

    async def get_questions_by_tags(self, tags: List[str]) -> List[Dict[str, Any]]:
        """Récupère les questions filtrées par tags."""
        return await self.get_questions(
            filters={"tags": {"$in": tags}},
            limit=1000
        )
    
    async def get_questions_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Récupère les questions dans une plage de dates."""
        return await self.get_questions(
            filters={
                "publication_date": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            },
            limit=1000
        )
    
    async def get_top_authors(self, limit: Optional[int] = 10) -> List[Dict[str, Any]]:
        """Récupère les auteurs les plus actifs."""
        authors_coll = self.motor_database[self.authors_collection]
        
        cursor = authors_coll.find().sort("question_count", -1)
        if limit is not None:
            cursor = cursor.limit(limit)
            authors = await cursor.to_list(length=limit)
        else:
            authors = await cursor.to_list(length=None)
        
        return authors

    async def get_authors_by_question_ids(self, question_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Récupère les auteurs correspondant aux questions spécifiées.
        
        Args:
            question_ids: Liste des IDs des questions
            
        Returns:
            Liste des auteurs uniques de ces questions
        """
        if not question_ids:
            return []
            
        questions_coll = self.motor_database[self.questions_collection]
        
        # Récupérer les noms d'auteurs uniques des questions spécifiées
        pipeline = [
            {"$match": {"question_id": {"$in": question_ids}}},
            {"$group": {"_id": "$author_name"}},
            {"$match": {"_id": {"$ne": None, "$ne": "Unknown"}}}
        ]
        
        cursor = questions_coll.aggregate(pipeline)
        author_names_docs = await cursor.to_list(length=None)
        author_names = [doc["_id"] for doc in author_names_docs]
        
        if not author_names:
            return []
            
        # Récupérer les détails des auteurs
        authors_coll = self.motor_database[self.authors_collection]
        cursor = authors_coll.find(
            {"author_name": {"$in": author_names}}
        ).sort("question_count", -1)
        
        authors = await cursor.to_list(length=None)
        return authors
    
    async def get_tag_statistics(self) -> List[Dict[str, Any]]:
        """Calcule les statistiques des tags."""
        questions_coll = self.motor_database[self.questions_collection]
        
        pipeline = [
            {"$unwind": "$tags"},
            {
                "$group": {
                    "_id": "$tags",
                    "count": {"$sum": 1},
                    "avg_votes": {"$avg": "$vote_count"},
                    "avg_views": {"$avg": "$view_count"}
                }
            },
            {"$sort": {"count": -1}},
            {"$limit": 50}
        ]
        
        cursor = questions_coll.aggregate(pipeline)
        stats = await cursor.to_list(length=50)
        
        return stats
    
    async def store_analysis_results(
        self,
        analysis_type: str,
        results: Dict[str, Any]
    ) -> None:
        """
        Stocke les résultats d'une analyse.
        
        Args:
            analysis_type: Type d'analyse effectuée
            results: Résultats de l'analyse
        """
        analysis_coll = self.motor_database[self.analysis_collection]
        
        analysis_doc = {
            "analysis_type": analysis_type,
            "analysis_date": datetime.utcnow(),
            "results": results,
            "metadata": {
                "total_questions_analyzed": results.get("total_questions", 0),
                "analysis_duration": results.get("duration", 0)
            }
        }
        
        await analysis_coll.insert_one(analysis_doc)
        self.logger.info(f"Résultats d'analyse '{analysis_type}' stockés")
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de la base de données."""
        questions_coll = self.motor_database[self.questions_collection]
        authors_coll = self.motor_database[self.authors_collection]
        analysis_coll = self.motor_database[self.analysis_collection]
        
        stats = {
            "questions_count": await questions_coll.count_documents({}),
            "authors_count": await authors_coll.count_documents({}),
            "analysis_count": await analysis_coll.count_documents({}),
            "last_question_date": None,
            "first_question_date": None
        }
        
        # Dates des questions
        latest_question = await questions_coll.find_one(
            sort=[("publication_date", -1)]
        )
        if latest_question:
            stats["last_question_date"] = latest_question["publication_date"]
        
        earliest_question = await questions_coll.find_one(
            sort=[("publication_date", 1)]
        )
        if earliest_question:
            stats["first_question_date"] = earliest_question["publication_date"]
        
        return stats
    
    async def export_data_to_json(self, output_file: str) -> None:
        """Exporte toutes les données vers un fichier JSON."""
        try:
            questions = await self.get_questions(limit=10000)
            authors = await self.get_top_authors(limit=1000)
            
            export_data = {
                "export_date": datetime.utcnow().isoformat(),
                "questions": questions,
                "authors": authors,
                "stats": await self.get_database_stats()
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"Données exportées vers {output_file}")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'export: {e}")
            raise
