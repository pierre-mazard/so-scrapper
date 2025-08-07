#!/usr/bin/env python3
"""
Stack Overflow Scraper - Main Script
====================================

Point d'entrée principal pour l'outil d'extraction de données Stack Overflow.
Ce script orchestre le processus de scraping, stockage et analyse des données.

Usage:
    python main.py [options]

Author: Pierre Mazard
Date: August 2025
"""

import argparse
import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict

from src.scraper import StackOverflowScraper, QuestionData
from src.database import DatabaseManager
from src.analyzer import DataAnalyzer
from src.config import Config


async def store_questions_update_only(db_manager: DatabaseManager, questions_data: List[QuestionData], logger) -> Dict[str, int]:
    """
    Stocke les questions en mode 'update-only' : met à jour seulement les questions/auteurs existants.
    
    Args:
        db_manager: Gestionnaire de base de données
        questions_data: Liste des questions à traiter
        logger: Logger pour les messages
        
    Returns:
        Dict avec les statistiques de stockage
    """
    logger.info("🔍 Mode UPDATE-ONLY : Mise à jour des questions existantes uniquement...")
    
    # Récupérer les IDs existants
    questions_coll = db_manager.motor_database[db_manager.questions_collection]
    existing_ids = set()
    
    async for doc in questions_coll.find({}, {"question_id": 1}):
        existing_ids.add(doc["question_id"])
    
    logger.info(f"📊 Questions existantes en base: {len(existing_ids)}")
    
    # Filtrer les questions existantes à mettre à jour
    update_questions = []
    for question in questions_data:
        if question.question_id in existing_ids:
            update_questions.append(question)
    
    logger.info(f"🔄 Questions à mettre à jour: {len(update_questions)}")
    logger.info(f"🚫 Questions nouvelles ignorées: {len(questions_data) - len(update_questions)}")
    
    if update_questions:
        # Mettre à jour uniquement les existantes
        return await db_manager.store_questions(update_questions, update_only=True)
    else:
        logger.info("ℹ️  Aucune question existante à mettre à jour")
        return {'questions_stored': 0, 'authors_new': 0, 'authors_updated': 0}


async def store_questions_append_only(db_manager: DatabaseManager, questions_data: List[QuestionData], logger) -> Dict[str, int]:
    """
    Stocke les questions en mode 'append-only' : ignore complètement les doublons.
    
    Args:
        db_manager: Gestionnaire de base de données
        questions_data: Liste des questions à stocker
        logger: Logger pour les messages
        
    Returns:
        Dict avec les statistiques de stockage
    """
    logger.info("🔍 Mode APPEND-ONLY : Filtrage des questions existantes...")
    
    # Récupérer les IDs existants
    questions_coll = db_manager.motor_database[db_manager.questions_collection]
    existing_ids = set()
    
    async for doc in questions_coll.find({}, {"question_id": 1}):
        existing_ids.add(doc["question_id"])
    
    logger.info(f"📊 Questions existantes en base: {len(existing_ids)}")
    
    # Filtrer les nouvelles questions
    new_questions = []
    for question in questions_data:
        if question.question_id not in existing_ids:
            new_questions.append(question)
    
    logger.info(f"✨ Nouvelles questions à ajouter: {len(new_questions)}")
    logger.info(f"🚫 Questions doublons ignorées: {len(questions_data) - len(new_questions)}")
    
    if new_questions:
        # Stocker uniquement les nouvelles
        return await db_manager.store_questions(new_questions)
    else:
        logger.info("ℹ️  Aucune nouvelle question à stocker")
        return {'questions_stored': 0, 'authors_new': 0, 'authors_updated': 0}


def setup_logging(log_level: str = "INFO") -> None:
    """Configure le système de logging."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/scraper.log'),
            logging.StreamHandler()
        ]
    )


async def main(
    max_questions: int = 100,
    tags: Optional[list] = None,
    use_api: bool = False,
    analyze_data: bool = True,
    storage_mode: str = "upsert",
    analysis_scope: str = "all"
) -> None:
    """
    Fonction principale pour exécuter le scraping et l'analyse.
    
    Args:
        max_questions: Nombre maximum de questions à scraper
        tags: Liste des tags à filtrer
        use_api: Utiliser l'API Stack Overflow au lieu du scraping
        analyze_data: Effectuer l'analyse des données après extraction
        storage_mode: Mode de stockage ("upsert", "update", "append-only")
        analysis_scope: Portée de l'analyse ("all", "new-only")
    """
    logger = logging.getLogger(__name__)
    logger.info("[START] DÉMARRAGE DU STACK OVERFLOW SCRAPER")
    logger.info("=" * 60)
    
    # Dictionnaire pour collecter les informations d'exécution
    execution_info = {
        'start_time': datetime.now().isoformat(),
        'max_questions': max_questions,
        'target_tags': tags or [],
        'extraction_mode': 'API Stack Overflow' if use_api else 'Scraping web',
        'storage_mode': storage_mode,
        'analysis_scope': analysis_scope
    }
    
    try:
        # Initialisation des composants
        logger.info("[INIT]  PHASE 0: Initialisation des composants...")
        config = Config()
        logger.info("[OK] Configuration chargée")
        
        db_manager = DatabaseManager(config.database_config)
        await db_manager.connect()  # Connexion à la base de données
        logger.info("[OK] Connexion à la base de données établie")
        
        # Afficher le mode de stockage choisi
        storage_modes = {
            "upsert": "🔄 Insert + Mise à jour (upsert - ajoute les nouvelles, met à jour les existantes)",
            "update": "🔄 Mise à jour uniquement (met à jour seulement les questions/auteurs existants)",
            "append-only": "➕ Ajout uniquement (filtre les questions existantes, ajoute seulement les nouvelles)"
        }
        logger.info(f"[MODE] {storage_modes.get(storage_mode, storage_mode)}")
        
        scraper = StackOverflowScraper({
            **config.scraper_config.__dict__,
            'api': config.api_config.__dict__
        })
        await scraper.setup_session()  # Initialisation de la session
        logger.info("[OK] Session de scraping initialisée")
        logger.info("[READY] Initialisation terminée - Début du processus principal...")
        logger.info("-" * 60)
        
        # Extraction des données
        logger.info(f"[EXTRACT] PHASE 1: Extraction de {max_questions} questions...")
        logger.info(f"Tags ciblés: {tags if tags else 'Tous les tags'}")
        logger.info(f"Mode: {execution_info['extraction_mode']}")
        
        start_time = datetime.now()
        scraping_start = start_time
        if use_api:
            questions_data = await scraper.fetch_via_api(
                max_questions=max_questions,
                tags=tags
            )
        else:
            questions_data = await scraper.scrape_questions(
                max_questions=max_questions,
                tags=tags
            )
        
        extraction_time = datetime.now() - scraping_start
        execution_info.update({
            'scraping_duration': extraction_time.total_seconds(),
            'questions_extracted': len(questions_data),
            'extraction_rate': len(questions_data) / extraction_time.total_seconds() if extraction_time.total_seconds() > 0 else 0,
            'scraping_status': '✅ Terminé'
        })
        
        # Calcul des statistiques d'extraction
        unique_authors = set()
        unique_tags = set()
        for question in questions_data:
            if question.author_name:
                unique_authors.add(question.author_name)
            if question.tags:
                unique_tags.update(question.tags)
        
        execution_info.update({
            'unique_authors': len(unique_authors),
            'unique_tags': len(unique_tags)
        })
        
        logger.info(f"[OK] Extraction terminée: {len(questions_data)} questions récupérées en {extraction_time.total_seconds():.1f}s")
        
        # Stockage en base de données avec mode intelligent
        logger.info("[STORE] PHASE 2: Stockage des données en base...")
        logger.info(f"Données à stocker: {len(questions_data)} questions")
        logger.info(f"Mode de stockage: {storage_mode}")
        
        storage_start = datetime.now()
        new_questions_ids = []  # Pour traquer les nouvelles questions
        
        if storage_mode == "upsert":
            # Mode par défaut : insert + mise à jour (upsert)
            storage_result = await db_manager.store_questions(questions_data)
            stored_count = storage_result['questions_stored']
            authors_new = storage_result['authors_new']
            authors_updated = storage_result['authors_updated']
            # En mode upsert, on considère toutes les questions comme "nouvelles" pour l'analyse
            new_questions_ids = [q.question_id for q in questions_data]
            
        elif storage_mode == "update":
            # Mode mise à jour uniquement : met à jour seulement les existantes
            storage_result = await store_questions_update_only(db_manager, questions_data, logger)
            stored_count = storage_result['questions_stored']
            authors_new = storage_result['authors_new']
            authors_updated = storage_result['authors_updated']
            # En mode update, seules les questions mises à jour sont considérées comme "nouvelles" pour l'analyse
            existing_ids = await db_manager.get_question_ids()
            new_questions_ids = [q.question_id for q in questions_data if q.question_id in existing_ids]
            
        elif storage_mode == "append-only":
            # Mode ajout uniquement : ignore les doublons
            # Récupérer les IDs existants pour identifier les nouvelles
            existing_ids = await db_manager.get_question_ids()
            before_count = len(existing_ids)
            
            storage_result = await store_questions_append_only(db_manager, questions_data, logger)
            stored_count = storage_result['questions_stored']
            authors_new = storage_result['authors_new']
            authors_updated = storage_result['authors_updated']
            
            # Identifier les nouvelles questions (celles qui ont été réellement ajoutées)
            new_questions_ids = [q.question_id for q in questions_data if q.question_id not in existing_ids]
            
        execution_info.update({
            'new_questions_count': len(new_questions_ids),
            'new_questions_ids': new_questions_ids
        })
        
        storage_time = datetime.now() - storage_start
        
        # Log des détails d'auteurs 
        if authors_new > 0:
            logger.info(f"👥 Nouveaux auteurs ajoutés: {authors_new}")
        if authors_updated > 0:
            logger.info(f"🔄 Auteurs mis à jour: {authors_updated}")
        if authors_new == 0 and authors_updated == 0 and stored_count == 0:
            logger.info("ℹ️  Aucun auteur ajouté ou mis à jour")
        
        execution_info.update({
            'storage_duration': storage_time.total_seconds(),
            'questions_stored': stored_count,
            'questions_attempted': len(questions_data),
            'authors_new': authors_new,
            'authors_updated': authors_updated,
            'authors_total_affected': authors_new + authors_updated,
            'storage_rate': stored_count / storage_time.total_seconds() if storage_time.total_seconds() > 0 else 0,
            'storage_status': '✅ Terminé',
            'storage_mode': storage_mode
        })
        
        logger.info(f"[OK] Stockage terminé en {storage_time.total_seconds():.1f}s")
        logger.info(f"📊 Bilan: {stored_count}/{len(questions_data)} questions stockées")
        
        # Analyse des données
        if analyze_data:
            logger.info("[ANALYZE] PHASE 3: Analyse des données...")
            logger.info("Initialisation de l'analyseur...")
            
            analyzer = DataAnalyzer(db_manager)
            
            # Passer les informations d'exécution à l'analyseur
            total_time_so_far = (datetime.now() - start_time).total_seconds()
            execution_info['total_duration_so_far'] = total_time_so_far
            analyzer.set_execution_metadata(execution_info)
            
            # Déterminer les questions à analyser selon l'analysis_scope
            questions_to_analyze = None
            if analysis_scope == "new-only":
                if new_questions_ids:
                    questions_to_analyze = new_questions_ids
                    logger.info(f"🎯 Analyse limitée aux {len(new_questions_ids)} nouvelles questions")
                else:
                    logger.warning("⚠️ Aucune nouvelle question trouvée, analyse annulée")
                    execution_info.update({
                        'analysis_status': '⚠️ Annulée - Aucune nouvelle question',
                        'analysis_scope': analysis_scope
                    })
                    logger.info("⏭️  Analyse annulée")
                    questions_to_analyze = "skip"
            else:
                logger.info("🎯 Analyse de toutes les questions disponibles")
            
            if questions_to_analyze != "skip":
                analysis_start = datetime.now()
                logger.info("Démarrage de l'analyse des tendances...")
                
                # Passer les IDs des questions à analyser (None = toutes les questions)
                analysis_results = await analyzer.analyze_trends(question_ids=questions_to_analyze)
                analysis_time = datetime.now() - analysis_start
                
                analyzed_count = len(questions_to_analyze) if questions_to_analyze else "toutes"
                execution_info.update({
                    'analysis_duration': analysis_time.total_seconds(),
                    'analysis_status': '✅ Terminé',
                    'analysis_scope': analysis_scope,
                    'analyzed_questions_count': analyzed_count
                })
                
                logger.info(f"[OK] Analyse terminée en {analysis_time.total_seconds():.1f}s")
                
                # Sauvegarde des résultats d'analyse (sans visualisations)
                logger.info("[SAVE] Sauvegarde des résultats...")
                save_start = datetime.now()
                await analyzer.save_results(analysis_results)
                save_time = datetime.now() - save_start
                
                execution_info.update({
                    'save_duration': save_time.total_seconds()
                })
                
                logger.info(f"[OK] Sauvegarde terminée en {save_time.total_seconds():.1f}s")
            else:
                # Générer un rapport même si l'analyse est annulée
                logger.info("[REPORT] Génération d'un rapport d'exécution...")
                save_start = datetime.now()
                
                # Créer un résultat vide avec les informations d'exécution
                empty_results = {
                    'execution_info': execution_info,
                    'analysis_skipped': True,
                    'skip_reason': execution_info.get('analysis_skipped_reason', 'Aucune nouvelle question à analyser')
                }
                
                await analyzer.save_results(empty_results)
                save_time = datetime.now() - save_start
                
                execution_info.update({
                    'save_duration': save_time.total_seconds()
                })
                
                logger.info(f"[OK] Rapport d'exécution généré en {save_time.total_seconds():.1f}s")
        else:
            logger.info("⏭️  Analyse des données désactivée")
            
            # Modifier les informations d'exécution pour refléter que l'analyse est désactivée
            execution_info['analysis_scope'] = 'disabled'
            
            # Générer un rapport même si l'analyse est désactivée
            logger.info("[REPORT] Génération d'un rapport d'exécution...")
            save_start = datetime.now()
            
            # Créer un DataAnalyzer pour générer le rapport
            analyzer = DataAnalyzer(db_manager)
            analyzer.set_execution_metadata(execution_info)
            
            # Créer un résultat vide avec les informations d'exécution
            disabled_results = {
                'execution_info': execution_info,
                'analysis_disabled': True,
                'skip_reason': 'Analyse désactivée par l\'utilisateur (--no-analysis)'
            }
            
            await analyzer.save_results(disabled_results)
            save_time = datetime.now() - save_start
            
            execution_info.update({
                'save_duration': save_time.total_seconds(),
                'analysis_status': '⏭️ Désactivée'
            })
            
            logger.info(f"[OK] Rapport d'exécution généré en {save_time.total_seconds():.1f}s")
            execution_info.update({
                'analysis_status': '⏭️ Désactivée'
            })
        
        total_time = datetime.now() - start_time
        execution_info['total_duration'] = total_time.total_seconds()
        
        logger.info("🎉 PROCESSUS TERMINÉ AVEC SUCCÈS!")
        logger.info(f"Temps total:  Temps total d'exécution: {total_time.total_seconds():.1f}s")
        logger.info(f"Questions extraites: Résumé: {len(questions_data)} questions traitées")
        
        # Fermeture des connexions
        logger.info("🔌 Fermeture des connexions...")
        await db_manager.disconnect()
        await scraper.close()
        logger.info("[OK] Toutes les connexions fermées")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution : {e}")
        # Nettoyage en cas d'erreur
        try:
            if 'db_manager' in locals():
                await db_manager.disconnect()
            if 'scraper' in locals():
                await scraper.close()
        except:
            pass
        raise


def parse_arguments():
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(
        description="Stack Overflow Data Scraper and Analyzer"
    )
    
    parser.add_argument(
        "--max-questions", "-n",
        type=int,
        default=300,
        help="Nombre maximum de questions à extraire (défaut: 300)"
    )
    
    parser.add_argument(
        "--tags", "-t",
        nargs="+",
        help="Tags à filtrer (ex: python javascript react)"
    )
    
    parser.add_argument(
        "--use-api",
        action="store_true",
        help="Utiliser l'API Stack Overflow au lieu du scraping"
    )
    
    parser.add_argument(
        "--no-analysis",
        action="store_true",
        help="Désactiver l'analyse des données"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Niveau de logging (défaut: INFO)"
    )
    
    parser.add_argument(
        "--mode",
        choices=["upsert", "update", "append-only"],
        default="upsert",
        help="Mode de stockage des questions (défaut: upsert)\n"
             "upsert: Insert nouvelles + met à jour existantes (comportement par défaut)\n"
             "update: Met à jour seulement les questions/auteurs existants (pas d'ajout)\n"
             "append-only: Ajoute seulement les nouvelles questions (filtre les existantes)"
    )
    
    parser.add_argument(
        "--analysis-scope",
        choices=["all", "new-only"],
        default="all",
        help="Portée de l'analyse (défaut: all)\n"
             "all: Analyse toutes les questions dans la base de données\n"
             "new-only: Analyse seulement les questions nouvellement ajoutées/mises à jour"
    )
    
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    setup_logging(args.log_level)
    
    # Exécution asynchrone du scraper
    asyncio.run(main(
        max_questions=args.max_questions,
        tags=args.tags,
        use_api=args.use_api,
        analyze_data=not args.no_analysis,
        storage_mode=args.mode,
        analysis_scope=args.analysis_scope
    ))
