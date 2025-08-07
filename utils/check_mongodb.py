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


def analyze_collections(db, collections):
    """Analyse détaillée des collections MongoDB."""
    for coll_name in collections:
        collection = db[coll_name]
        count = collection.count_documents({})
        
        print(f"\n📄 Collection: {coll_name}")
        print("-" * 40)
        print(f"📊 Nombre de documents: {count:,}")
        
        # Ignorer les détails pour la collection analysis (trop volumineuse)
        if coll_name == "analysis":
            print("   ℹ️  Collection d'analyses (détails masqués pour la lisibilité)")
            continue
        
        if count > 0:
            # Analyser la structure des documents
            print("🔍 Structure des documents:")
            analyze_document_structure(collection)
            
            # Statistiques générales
            print("📈 Statistiques:")
            analyze_collection_stats(collection, coll_name)
            
            # Index de la collection
            print("🗂️  Index:")
            analyze_collection_indexes(collection)
        else:
            print("   ⚪ Collection vide")


def analyze_document_structure(collection):
    """Analyse la structure des documents dans une collection."""
    # Prendre un échantillon de documents pour analyser la structure
    sample_size = min(100, collection.count_documents({}))
    pipeline = [{"$sample": {"size": sample_size}}]
    
    field_types = {}
    field_examples = {}
    
    for doc in collection.aggregate(pipeline):
        analyze_document_fields(doc, field_types, field_examples, "")
    
    # Afficher les champs trouvés
    for field_path, type_info in sorted(field_types.items()):
        types_list = list(type_info.keys())
        example = field_examples.get(field_path, "N/A")
        
        if len(types_list) == 1:
            type_str = types_list[0]
        else:
            type_str = f"Mixte ({', '.join(types_list)})"
        
        # Tronquer l'exemple s'il est trop long
        if isinstance(example, str) and len(example) > 50:
            example = example[:47] + "..."
        
        print(f"   • {field_path:<25} : {type_str:<15} (ex: {example})")


def analyze_document_fields(doc, field_types, field_examples, prefix=""):
    """Analyse récursive des champs d'un document."""
    for key, value in doc.items():
        if key == "_id":
            continue  # Ignorer l'ID MongoDB
            
        field_path = f"{prefix}.{key}" if prefix else key
        value_type = type(value).__name__
        
        # Gérer les types spéciaux
        if value_type == "ObjectId":
            value_type = "ObjectId"
        elif value_type == "datetime":
            value_type = "DateTime"
        elif isinstance(value, list):
            if value:
                inner_type = type(value[0]).__name__
                value_type = f"Array[{inner_type}]"
            else:
                value_type = "Array[empty]"
        elif isinstance(value, dict):
            value_type = "Object"
            # Analyser récursivement les objets imbriqués
            analyze_document_fields(value, field_types, field_examples, field_path)
            continue
        
        # Enregistrer le type
        if field_path not in field_types:
            field_types[field_path] = {}
        if value_type not in field_types[field_path]:
            field_types[field_path][value_type] = 0
        field_types[field_path][value_type] += 1
        
        # Enregistrer un exemple (seulement le premier trouvé)
        if field_path not in field_examples:
            field_examples[field_path] = value


def analyze_collection_stats(collection, coll_name):
    """Analyse les statistiques d'une collection."""
    try:
        # Taille de la collection
        stats = collection.database.command("collStats", coll_name)
        size_mb = stats.get("size", 0) / (1024 * 1024)
        avg_doc_size = stats.get("avgObjSize", 0)
        
        print(f"   💾 Taille: {size_mb:.2f} MB")
        print(f"   📏 Taille moyenne par document: {avg_doc_size:.0f} bytes")
        
        # Analyser les dates si présentes
        date_fields = ["created_at", "updated_at", "publication_date", "timestamp"]
        for date_field in date_fields:
            try:
                # Trouver la date la plus ancienne et la plus récente
                oldest = list(collection.find({date_field: {"$exists": True}}).sort(date_field, 1).limit(1))
                newest = list(collection.find({date_field: {"$exists": True}}).sort(date_field, -1).limit(1))
                
                if oldest and newest:
                    oldest_date = oldest[0][date_field]
                    newest_date = newest[0][date_field]
                    
                    # Formater les dates
                    if hasattr(oldest_date, 'strftime'):
                        oldest_str = oldest_date.strftime("%Y-%m-%d %H:%M")
                        newest_str = newest_date.strftime("%Y-%m-%d %H:%M")
                    else:
                        oldest_str = str(oldest_date)
                        newest_str = str(newest_date)
                    
                    print(f"   📅 {date_field}: {oldest_str} → {newest_str}")
            except:
                continue
                
        # Compter les champs numériques importants
        numeric_fields = ["score", "view_count", "answer_count", "question_id"]
        for num_field in numeric_fields:
            try:
                result = list(collection.aggregate([
                    {"$match": {num_field: {"$exists": True}}},
                    {"$group": {
                        "_id": None,
                        "min": {"$min": f"${num_field}"},
                        "max": {"$max": f"${num_field}"},
                        "avg": {"$avg": f"${num_field}"}
                    }}
                ]))
                
                if result:
                    stats = result[0]
                    print(f"   🔢 {num_field}: min={stats['min']}, max={stats['max']}, avg={stats['avg']:.1f}")
            except:
                continue
                
    except Exception as e:
        print(f"   ⚠️ Impossible de récupérer les statistiques: {e}")


def analyze_collection_indexes(collection):
    """Analyse les index d'une collection."""
    try:
        indexes = collection.list_indexes()
        index_count = 0
        
        for index in indexes:
            index_count += 1
            name = index.get("name", "Unnamed")
            keys = index.get("key", {})
            unique = index.get("unique", False)
            
            keys_str = ", ".join([f"{k}:{v}" for k, v in keys.items()])
            unique_str = " (UNIQUE)" if unique else ""
            
            print(f"   🗂️  {name}: {keys_str}{unique_str}")
        
        if index_count == 0:
            print("   ⚪ Aucun index personnalisé")
            
    except Exception as e:
        print(f"   ⚠️ Impossible de lister les index: {e}")


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
            
            # Analyse détaillée des collections
            print(f"\n🔍 ANALYSE DÉTAILLÉE DES COLLECTIONS")
            print("=" * 50)
            analyze_collections(project_db, collections)
        
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
