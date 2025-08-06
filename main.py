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
from typing import Optional

from src.scraper import StackOverflowScraper
from src.database import DatabaseManager
from src.analyzer import DataAnalyzer
from src.config import Config


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
    analyze_data: bool = True
) -> None:
    """
    Fonction principale pour exécuter le scraping et l'analyse.
    
    Args:
        max_questions: Nombre maximum de questions à scraper
        tags: Liste des tags à filtrer
        use_api: Utiliser l'API Stack Overflow au lieu du scraping
        analyze_data: Effectuer l'analyse des données après extraction
    """
    logger = logging.getLogger(__name__)
    logger.info("[START] DÉMARRAGE DU STACK OVERFLOW SCRAPER")
    logger.info("=" * 60)
    
    try:
        # Initialisation des composants
        logger.info("[INIT]  PHASE 0: Initialisation des composants...")
        config = Config()
        logger.info("[OK] Configuration chargée")
        
        db_manager = DatabaseManager(config.database_config)
        await db_manager.connect()  # Connexion à la base de données
        logger.info("[OK] Connexion à la base de données établie")
        
        scraper = StackOverflowScraper(config.scraper_config)
        await scraper.setup_session()  # Initialisation de la session
        logger.info("[OK] Session de scraping initialisée")
        logger.info("[READY] Initialisation terminée - Début du processus principal...")
        logger.info("-" * 60)
        
        # Extraction des données
        logger.info(f"[EXTRACT] PHASE 1: Extraction de {max_questions} questions...")
        logger.info(f"Tags ciblés: {tags if tags else 'Tous les tags'}")
        logger.info(f"Mode: {'API Stack Overflow' if use_api else 'Scraping web'}")
        
        start_time = datetime.now()
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
        
        extraction_time = datetime.now() - start_time
        logger.info(f"[OK] Extraction terminée: {len(questions_data)} questions récupérées en {extraction_time.total_seconds():.1f}s")
        
        # Stockage en base de données
        logger.info("[STORE] PHASE 2: Stockage des données en base...")
        logger.info(f"Données à stocker: {len(questions_data)} questions")
        
        storage_start = datetime.now()
        await db_manager.store_questions(questions_data)
        storage_time = datetime.now() - storage_start
        logger.info(f"[OK] Stockage terminé en {storage_time.total_seconds():.1f}s")
        
        # Analyse des données
        if analyze_data:
            logger.info("[ANALYZE] PHASE 3: Analyse des données...")
            logger.info("Initialisation de l'analyseur...")
            
            analyzer = DataAnalyzer(db_manager)
            analysis_start = datetime.now()
            logger.info("Démarrage de l'analyse des tendances...")
            
            analysis_results = await analyzer.analyze_trends()
            analysis_time = datetime.now() - analysis_start
            logger.info(f"[OK] Analyse terminée en {analysis_time.total_seconds():.1f}s")
            
            # Sauvegarde des résultats d'analyse
            logger.info("[STORE] Sauvegarde des résultats d'analyse...")
            save_start = datetime.now()
            await analyzer.save_results(analysis_results)
            
            # Génération des visualisations
            logger.info("[VIZ] Génération des visualisations...")
            await analyzer.generate_visualizations(analysis_results)
            
            save_time = datetime.now() - save_start
            logger.info(f"[OK] Sauvegarde et visualisations terminées en {save_time.total_seconds():.1f}s")
        else:
            logger.info("⏭️  Analyse des données désactivée")
        
        total_time = datetime.now() - start_time
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
    
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    setup_logging(args.log_level)
    
    # Exécution asynchrone du scraper
    asyncio.run(main(
        max_questions=args.max_questions,
        tags=args.tags,
        use_api=args.use_api,
        analyze_data=not args.no_analysis
    ))
