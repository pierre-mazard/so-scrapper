#!/usr/bin/env python3
"""
Script de nettoyage de la base de données
=========================================

Script utilitaire pour vider complètement la base de données MongoDB
du projet Stack Overflow Scraper.

Usage:
    python utils/clear_database.py
    
ATTENTION: Cette opération est irréversible!
"""

import sys
import pymongo
from pathlib import Path

# Ajouter le répertoire src au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from config import Config
    config = Config()
    db_config = config.database_config
    
    connection_url = f"mongodb://{db_config.host}:{db_config.port}/"
    database_name = db_config.name
    
except ImportError:
    # Configuration par défaut si le module config n'est pas disponible
    print("⚠️  Module config non trouvé, utilisation de la configuration par défaut")
    connection_url = "mongodb://localhost:27017/"
    database_name = "stackoverflow_data"


def clear_database():
    """Vide complètement la base de données."""
    print("🗑️  NETTOYAGE DE LA BASE DE DONNÉES")
    print("=" * 50)
    print(f"📍 URL de connexion: {connection_url}")
    print(f"📍 Base de données: {database_name}")
    print()
    
    # Demander confirmation
    print("⚠️  ATTENTION: Cette opération va supprimer TOUTES les données!")
    print("   - Questions")
    print("   - Auteurs") 
    print("   - Analyses")
    print()
    
    confirm = input("Êtes-vous sûr de vouloir continuer? (tapez 'OUI' pour confirmer): ")
    
    if confirm != 'OUI':
        print("❌ Opération annulée")
        return False
    
    try:
        # Connexion à MongoDB
        print("🔄 Connexion à MongoDB...")
        client = pymongo.MongoClient(connection_url, serverSelectionTimeoutMS=5000)
        
        # Test de connexion
        client.admin.command('ping')
        print('✅ MongoDB connecté avec succès!')
        
        # Accéder à la base de données
        db = client[database_name]
        
        # Lister les collections
        collections = db.list_collection_names()
        print(f"📂 Collections trouvées: {collections}")
        
        if not collections:
            print("ℹ️  Aucune collection trouvée - Base déjà vide")
            return True
        
        # Supprimer chaque collection
        for collection_name in collections:
            print(f"🗑️  Suppression de la collection '{collection_name}'...")
            result = db[collection_name].delete_many({})
            print(f"   ✅ {result.deleted_count} documents supprimés")
        
        print()
        print("🎉 Nettoyage terminé avec succès!")
        print("✅ Base de données: VIDE")
        print("✅ Prêt pour un nouveau scraping")
        
        return True
        
    except pymongo.errors.ServerSelectionTimeoutError:
        print('❌ Impossible de se connecter à MongoDB')
        print('💡 Vérifiez que le serveur MongoDB est démarré')
        return False
        
    except Exception as e:
        print(f'❌ Erreur inattendue: {e}')
        return False


def main():
    """Fonction principale."""
    success = clear_database()
    
    if success:
        print("\n🚀 Base de données prête pour un nouveau scraping!")
        sys.exit(0)
    else:
        print("\n🛑 Échec du nettoyage de la base de données")
        sys.exit(1)


if __name__ == "__main__":
    main()
