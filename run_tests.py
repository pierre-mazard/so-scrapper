#!/usr/bin/env python3
"""
Script de lancement des tests avec logging
=========================================

Script pour exécuter la suite de tests avec un logging complet
et générer automatiquement un rapport des résultats.
"""

import subprocess
import sys
import os
import time
from pathlib import Path


def run_tests_with_logging():
    """Exécute les tests avec logging complet."""
    
    print("🔬 LANCEMENT DE LA SUITE DE TESTS AVEC LOGGING")
    print("=" * 60)
    
    # S'assurer que nous sommes dans le bon répertoire
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    print(f"📁 Répertoire de travail: {script_dir}")
    print(f"⏰ Début d'exécution: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Commande pytest avec toutes les options de logging
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short"
    ]
    
    print("🚀 Commande d'exécution:")
    print(f"   {' '.join(cmd)}")
    print()
    
    # Exécuter les tests
    start_time = time.time()
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        exit_code = result.returncode
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrompus par l'utilisateur")
        exit_code = 130
    except Exception as e:
        print(f"\n❌ Erreur lors de l'exécution des tests: {e}")
        exit_code = 1
    
    duration = time.time() - start_time
    
    print()
    print("=" * 60)
    print("📊 RÉSULTATS DE L'EXÉCUTION")
    print("=" * 60)
    print(f"⏱️  Durée totale: {duration:.2f} secondes")
    print(f"🔚 Code de sortie: {exit_code}")
    
    # Interpréter le code de sortie
    if exit_code == 0:
        print("✅ Tous les tests ont réussi!")
    elif exit_code == 1:
        print("❌ Certains tests ont échoué")
    elif exit_code == 2:
        print("⚠️  Erreur d'exécution ou d'usage de pytest")
    elif exit_code == 3:
        print("🛑 Tests interrompus par l'utilisateur")
    elif exit_code == 4:
        print("⚠️  Erreur interne de pytest")
    elif exit_code == 5:
        print("🔍 Aucun test trouvé")
    else:
        print(f"⚠️  Code de sortie inattendu: {exit_code}")
    
    print()
    
    # Vérifier si les fichiers de log ont été créés
    logs_dir = Path("tests/logs")
    if logs_dir.exists():
        log_files = list(logs_dir.glob("*.log"))
        if log_files:
            print("📄 Fichiers de log générés:")
            for log_file in sorted(log_files, key=os.path.getmtime, reverse=True)[:3]:
                size = log_file.stat().st_size
                size_str = f"{size} bytes" if size < 1024 else f"{size/1024:.1f} KB"
                print(f"   • {log_file.name} ({size_str})")
    
    print()
    print("💡 Pour analyser les résultats détaillés:")
    print("   python tests/analyze_logs.py --show")
    print()
    
    return exit_code


if __name__ == "__main__":
    exit_code = run_tests_with_logging()
    sys.exit(exit_code)
