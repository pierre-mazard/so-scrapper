#!/usr/bin/env python3
"""
Script de vérification MongoDB
=============================

Script utilitaire pour vérifier la configuration et la connectivité MongoDB
pour le projet Stack Overflow Scraper.

Usage:
    python scripts/check_mongodb.py
    
Vérifie:
- Connexion au serveur MongoDB
- Permissions de lecture/écriture
- Configuration de la base de données du projet
- Affichage des informations du serveur
"""

import sys
import pymongo
import time
from pathlib import Path

# Ajouter le répertoire src au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from config import Config
    config = Config()
    db_config = config.database_config
    
    connection_url = f"mongodb://{db_config.host}:{db_config.port}/"
    database_name = db_config.name
    collection_name = db_config.collection
    
except ImportError:
    # Configuration par défaut si le module config n'est pas disponible
    print("⚠️  Module config non trouvé, utilisation de la configuration par défaut")
    connection_url = "mongodb://localhost:27017/"
    database_name = "stackoverflow_data"
    collection_name = "questions"


def check_mongodb_connection():
    """Vérifie la connexion MongoDB."""
    print("🔍 VÉRIFICATION DE LA CONFIGURATION MONGODB")
    print("=" * 50)
    print(f"📍 URL de connexion: {connection_url}")
    print(f"📍 Base de données: {database_name}")
    print(f"📍 Collection: {collection_name}")
    print()
    
    try:
        # Connexion à MongoDB avec timeout court
        client = pymongo.MongoClient(
            connection_url, 
            serverSelectionTimeoutMS=5000
        )
        
        # Test de connexion (ping)
        print("🔄 Test de connexion...")
        client.admin.command('ping')
        print('✅ MongoDB connecté avec succès!')
        
        # Afficher les informations du serveur
        info = client.server_info()
        print(f'📊 Version MongoDB: {info["version"]}')
        print(f'📊 Plateforme: {info.get("gitVersion", "Non disponible")}')
        print()
        
        # Accéder à la base de données du projet
        db = client[database_name]
        collection = db[collection_name]
        
        # Test d'écriture
        print("🔄 Test d'écriture...")
        test_doc = {
            'test': 'connection_check',
            'timestamp': time.time(),
            'project': 'so-scrapper',
            'script': 'check_mongodb.py'
        }
        result = collection.insert_one(test_doc)
        print(f'✅ Document test inséré avec ID: {result.inserted_id}')
        
        # Test de lecture
        print("🔄 Test de lecture...")
        found_doc = collection.find_one({'test': 'connection_check'})
        if found_doc:
            print('✅ Document test lu avec succès!')
            
            # Nettoyer le test
            collection.delete_one({'_id': result.inserted_id})
            print('✅ Document test nettoyé!')
        else:
            print('❌ Impossible de lire le document test!')
            return False
        
        # Lister les bases de données
        print()
        print("📁 Bases de données disponibles:")
        databases = client.list_database_names()
        for db_name in databases:
            emoji = "🗂️" if db_name == database_name else "📂"
            print(f'   {emoji} {db_name}')
        
        # Informations sur la base de données du projet
        if database_name in databases:
            project_db = client[database_name]
            collections = project_db.list_collection_names()
            print(f"\n📋 Collections dans '{database_name}':")
            for coll_name in collections:
                emoji = "📄" if coll_name == collection_name else "📃"
                count = project_db[coll_name].count_documents({})
                print(f'   {emoji} {coll_name} ({count} documents)')
        
        print()
        print('🎉 MongoDB est parfaitement configuré pour le projet!')
        print('✅ Connexion: OK')
        print('✅ Lecture: OK') 
        print('✅ Écriture: OK')
        print('✅ Configuration: OK')
        
        return True
        
    except pymongo.errors.ServerSelectionTimeoutError:
        print('❌ Impossible de se connecter à MongoDB')
        print('💡 Vérifiez que le serveur MongoDB est démarré:')
        print('   - Windows: Démarrer le service MongoDB')
        print('   - macOS: brew services start mongodb')
        print('   - Linux: sudo systemctl start mongodb')
        return False
        
    except pymongo.errors.OperationFailure as e:
        print(f'❌ Erreur d\'opération MongoDB: {e}')
        print('💡 Vérifiez les permissions d\'accès à la base de données')
        return False
        
    except Exception as e:
        print(f'❌ Erreur inattendue: {e}')
        print('💡 Vérifiez la configuration MongoDB')
        return False


def main():
    """Fonction principale."""
    success = check_mongodb_connection()
    
    if success:
        print("\n🚀 MongoDB est prêt pour le projet Stack Overflow Scraper!")
        sys.exit(0)
    else:
        print("\n🛑 Résolvez les problèmes MongoDB avant de continuer")
        sys.exit(1)


if __name__ == "__main__":
    main()
