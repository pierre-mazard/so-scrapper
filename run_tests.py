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
from datetime import datetime


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


def generate_test_report():
    """Génère automatiquement un rapport de tests et le sauvegarde dans output/reports."""
    
    print("📊 GÉNÉRATION DU RAPPORT DE TESTS")
    print("=" * 40)
    
    try:
        # Importer l'analyseur de logs
        sys.path.append(str(Path(__file__).parent / "tests"))
        from analyze_logs import TestLogAnalyzer
        
        # Initialiser l'analyseur
        analyzer = TestLogAnalyzer()
        
        # Récupérer les derniers logs
        log_files = analyzer.get_latest_logs()
        
        if not log_files:
            print("❌ Aucun fichier de log trouvé pour générer le rapport!")
            return False
            
        print("📁 Analyse des fichiers de log:")
        for log_type, path in log_files.items():
            print(f"  • {log_type}: {path.name}")
        
        # Analyser les résultats
        main_log = log_files.get('run')
        if not main_log:
            print("❌ Fichier de log principal non trouvé!")
            return False
            
        results = analyzer.parse_test_results(main_log)
        
        # Générer le rapport
        report = analyzer.generate_report(results)
        
        # Créer le répertoire output/reports s'il n'existe pas
        reports_dir = Path("output/reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Nom du fichier de rapport avec timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"rapport_tests_{timestamp}.md"
        report_path = reports_dir / report_filename
        
        # Convertir le rapport en format Markdown
        markdown_report = convert_to_markdown(report, results)
        
        # Sauvegarder le rapport
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(markdown_report)
        
        print(f"✅ Rapport généré avec succès: {report_path}")
        print(f"📄 Taille du rapport: {report_path.stat().st_size} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la génération du rapport: {e}")
        return False


def convert_to_markdown(report: str, results: dict) -> str:
    """Convertit le rapport texte en format Markdown."""
    
    timestamp = datetime.now().strftime("%Y-%m-%d à %H:%M:%S")
    total_tests = len(results['passed']) + len(results['failed']) + len(results.get('errors', [])) + len(results['skipped'])
    success_rate = len(results['passed']) / total_tests * 100 if total_tests > 0 else 0
    
    markdown = f"""# 🧪 RAPPORT DE TESTS - STACK OVERFLOW SCRAPER

*Rapport d'exécution de la suite de tests*

---

## 📊 RÉSUMÉ EXÉCUTIF

### Informations générales

- **Date d'exécution**: {timestamp}
- **Tests totaux exécutés**: {total_tests}
- **Durée totale**: {results['total_duration']:.2f} secondes
- **Taux de réussite**: {success_rate:.1f}%

### Résultats par catégorie

| Statut | Nombre | Pourcentage |
|--------|--------|-------------|
| ✅ **Réussis** | {len(results['passed'])} | {len(results['passed'])/total_tests*100:.1f}% |
| ❌ **Échoués** | {len(results['failed'])} | {len(results['failed'])/total_tests*100:.1f}% |
| 🚫 **Erreurs** | {len(results.get('errors', []))} | {len(results.get('errors', []))/total_tests*100:.1f}% |
| ⏭️ **Ignorés** | {len(results['skipped'])} | {len(results['skipped'])/total_tests*100:.1f}% |

## 📈 ANALYSE DÉTAILLÉE

"""

    # Ajouter les tests réussis
    if results['passed']:
        markdown += f"""### ✅ Tests Réussis ({len(results['passed'])})

| Test | Durée |
|------|-------|
"""
        for test in results['passed']:
            markdown += f"| `{test['name']}` | {test['duration']:.2f}s |\n"
        markdown += "\n"

    # Ajouter les erreurs de tests
    if results.get('errors'):
        markdown += f"""### 🚫 Erreurs de Tests ({len(results['errors'])})

| Test | Durée | Détails |
|------|-------|---------|
"""
        for test in results['errors']:
            markdown += f"| `{test['name']}` | {test['duration']:.2f}s | ⚠️ Erreur de configuration/setup |\n"
        markdown += "\n"

    # Ajouter les tests échoués
    if results['failed']:
        markdown += f"""### ❌ Tests Échoués ({len(results['failed'])})

| Test | Durée | Détails |
|------|-------|---------|
"""
        for test in results['failed']:
            markdown += f"| `{test['name']}` | {test['duration']:.2f}s | ⚠️ Assertion échouée |\n"
        markdown += "\n"

    # Ajouter les tests ignorés
    if results['skipped']:
        markdown += f"""### ⏭️ Tests Ignorés ({len(results['skipped'])})

| Test | Raison |
|------|--------|
"""
        for test in results['skipped']:
            markdown += f"| `{test['name']}` | Ignoré |\n"
        markdown += "\n"

    # Tests les plus lents
    if results['passed'] or results['failed'] or results.get('errors'):
        all_timed_tests = results['passed'] + results['failed'] + results.get('errors', [])
        slowest = sorted(all_timed_tests, key=lambda x: x['duration'], reverse=True)[:5]
        
        markdown += f"""### 🐌 Tests les Plus Lents

| Rang | Test | Durée | Statut |
|------|------|-------|--------|
"""
        for i, test in enumerate(slowest, 1):
            if test in results['passed']:
                status = "✅ Réussi"
            elif test in results['failed']:
                status = "❌ Échoué"
            else:
                status = "🚫 Erreur"
            markdown += f"| {i} | `{test['name']}` | {test['duration']:.2f}s | {status} |\n"
        markdown += "\n"

    # Recommandations
    markdown += """## 💡 RECOMMANDATIONS

"""
    
    if results.get('errors'):
        markdown += "- 🚫 **Priorité critique**: Corriger les erreurs de configuration/setup listées ci-dessus\n"
    
    if results['failed']:
        markdown += "- 🔧 **Priorité haute**: Corriger les tests échoués (assertions) listés ci-dessus\n"
    
    if len(results['skipped']) > len(results['passed']) / 4:
        markdown += "- 🔍 **Analyse requise**: Beaucoup de tests ignorés - vérifier s'ils peuvent être activés\n"
    
    if results['total_duration'] > 60:
        markdown += "- ⚡ **Optimisation**: Durée d'exécution élevée - optimiser les tests les plus lents\n"
    
    if not results['failed'] and not results.get('errors') and not results['skipped']:
        markdown += "- 🎉 **Excellent**: Tous les tests passent avec succès!\n"
    elif not results['failed'] and not results.get('errors'):
        markdown += "- 🎉 **Très bon**: Tous les tests actifs passent avec succès!\n"

    markdown += f"""
## 📋 DÉTAILS TECHNIQUES

### Configuration de test

- **Framework**: pytest
- **Répertoire de tests**: `tests/`
- **Mode d'exécution**: Verbeux avec traces courtes
- **Logs générés**: `tests/logs/`

### Performance

- **Vitesse moyenne**: {total_tests/results['total_duration']:.1f} tests/seconde
- **Test le plus rapide**: {min([t['duration'] for t in results['passed'] + results['failed']] or [0]):.3f}s
- **Test le plus lent**: {max([t['duration'] for t in results['passed'] + results['failed']] or [0]):.3f}s

---
**Rapport généré le {timestamp}**  
*Stack Overflow Scraper - Suite de tests automatisée*
"""

    return markdown


if __name__ == "__main__":
    exit_code = run_tests_with_logging()
    
    # Générer automatiquement le rapport de tests
    print()
    print("🔄 GÉNÉRATION AUTOMATIQUE DU RAPPORT")
    print("=" * 40)
    
    if generate_test_report():
        print("✅ Rapport de tests généré avec succès!")
    else:
        print("⚠️ Impossible de générer le rapport de tests")
    
    print()
    sys.exit(exit_code)
