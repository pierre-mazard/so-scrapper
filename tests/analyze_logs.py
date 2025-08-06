#!/usr/bin/env python3
"""
Analyseur de logs de tests
=========================

Script pour analyser et afficher les résultats des tests à partir des fichiers de log.
Génère des rapports détaillés et des statistiques.
"""

import argparse
import re
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


class TestLogAnalyzer:
    """Analyseur de logs de tests."""
    
    def __init__(self, logs_dir: str = None):
        """Initialise l'analyseur."""
        if logs_dir is None:
            logs_dir = Path(__file__).parent / "logs"
        self.logs_dir = Path(logs_dir)
        
    def get_latest_logs(self) -> Dict[str, Path]:
        """Récupère les derniers fichiers de log."""
        log_files = {}
        
        # Chercher les fichiers de log les plus récents
        for pattern in ['test_run_*.log', 'test_errors_*.log', 'test_summary_*.log']:
            files = list(self.logs_dir.glob(pattern))
            if files:
                # Trier par date de modification (le plus récent en premier)
                latest = max(files, key=os.path.getmtime)
                log_type = pattern.split('_')[1].replace('*.log', '')
                log_files[log_type] = latest
                
        return log_files
    
    def parse_test_results(self, log_file: Path) -> Dict:
        """Parse les résultats des tests depuis le fichier de log."""
        results = {
            'passed': [],
            'failed': [],
            'skipped': [],
            'total_duration': 0,
            'start_time': None,
            'end_time': None
        }
        
        if not log_file.exists():
            return results
            
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Patterns pour extraire les informations
        patterns = {
            'passed': r'✅ RÉUSSI: ([^(]+)(?:\(([0-9.]+)s\))?',
            'failed': r'❌ ÉCHEC: ([^(]+)(?:\(([0-9.]+)s\))?',
            'skipped': r'⏭️  IGNORÉ: ([^\n]+)',
            'start': r'🔬 DÉBUT DE LA SESSION DE TESTS',
            'end': r'🏁 FIN DE LA SESSION DE TESTS',
            'duration': r'Durée totale: ([0-9.]+) secondes'
        }
        
        # Extraire les tests réussis
        for match in re.finditer(patterns['passed'], content):
            test_name = match.group(1).strip()
            duration = float(match.group(2)) if match.group(2) else 0
            results['passed'].append({'name': test_name, 'duration': duration})
            
        # Extraire les tests échoués
        for match in re.finditer(patterns['failed'], content):
            test_name = match.group(1).strip()
            duration = float(match.group(2)) if match.group(2) else 0
            results['failed'].append({'name': test_name, 'duration': duration})
            
        # Extraire les tests ignorés
        for match in re.finditer(patterns['skipped'], content):
            test_name = match.group(1).strip()
            results['skipped'].append({'name': test_name})
            
        # Extraire la durée totale
        duration_match = re.search(patterns['duration'], content)
        if duration_match:
            results['total_duration'] = float(duration_match.group(1))
            
        return results
    
    def generate_report(self, results: Dict) -> str:
        """Génère un rapport textuel des résultats."""
        report = []
        report.append("=" * 60)
        report.append("RAPPORT D'ANALYSE DES TESTS")
        report.append("=" * 60)
        report.append(f"Généré le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Statistiques globales
        total_tests = len(results['passed']) + len(results['failed']) + len(results['skipped'])
        report.append("📊 STATISTIQUES GLOBALES")
        report.append("-" * 30)
        report.append(f"Tests totaux:      {total_tests}")
        report.append(f"✅ Réussis:        {len(results['passed'])} ({len(results['passed'])/total_tests*100:.1f}%)")
        report.append(f"❌ Échoués:        {len(results['failed'])} ({len(results['failed'])/total_tests*100:.1f}%)")
        report.append(f"⏭️  Ignorés:        {len(results['skipped'])} ({len(results['skipped'])/total_tests*100:.1f}%)")
        report.append(f"⏱️  Durée totale:   {results['total_duration']:.2f}s")
        report.append("")
        
        # Tests les plus lents
        if results['passed'] or results['failed']:
            all_timed_tests = results['passed'] + results['failed']
            slowest = sorted(all_timed_tests, key=lambda x: x['duration'], reverse=True)[:5]
            
            report.append("🐌 TESTS LES PLUS LENTS")
            report.append("-" * 30)
            for i, test in enumerate(slowest, 1):
                status = "✅" if test in results['passed'] else "❌"
                report.append(f"{i}. {status} {test['name']} ({test['duration']:.2f}s)")
            report.append("")
        
        # Détail des échecs
        if results['failed']:
            report.append("❌ DÉTAIL DES ÉCHECS")
            report.append("-" * 30)
            for test in results['failed']:
                report.append(f"• {test['name']} ({test['duration']:.2f}s)")
            report.append("")
        
        # Tests ignorés
        if results['skipped']:
            report.append("⏭️  TESTS IGNORÉS")
            report.append("-" * 30)
            for test in results['skipped']:
                report.append(f"• {test['name']}")
            report.append("")
        
        # Recommandations
        report.append("💡 RECOMMANDATIONS")
        report.append("-" * 30)
        if results['failed']:
            report.append("• Corriger les tests échoués en priorité")
        if len(results['skipped']) > len(results['passed']) / 4:
            report.append("• Beaucoup de tests ignorés - vérifier s'ils peuvent être activés")
        if results['total_duration'] > 60:
            report.append("• Durée d'exécution élevée - optimiser les tests les plus lents")
        if not results['failed'] and not results['skipped']:
            report.append("• 🎉 Excellente couverture de tests! Tous les tests passent.")
        elif not results['failed']:
            report.append("• 🎉 Excellente couverture de tests! Tous les tests passent.")
            
        report.append("="*60)
        
        return "\n".join(report)
    
    def save_report(self, report: str, filename: str = None) -> Path:
        """Sauvegarde le rapport dans un fichier."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_report_{timestamp}.txt"
            
        report_path = self.logs_dir / filename
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
            
        return report_path


def main():
    """Fonction principale du script."""
    parser = argparse.ArgumentParser(description="Analyseur de logs de tests")
    parser.add_argument('--logs-dir', help="Répertoire des logs (par défaut: tests/logs)")
    parser.add_argument('--output', help="Fichier de sortie pour le rapport")
    parser.add_argument('--show', action='store_true', help="Afficher le rapport dans la console")
    
    args = parser.parse_args()
    
    # Initialiser l'analyseur
    analyzer = TestLogAnalyzer(args.logs_dir)
    
    # Récupérer les derniers logs
    log_files = analyzer.get_latest_logs()
    
    if not log_files:
        print("❌ Aucun fichier de log trouvé!")
        return 1
        
    print("📁 Fichiers de log trouvés:")
    for log_type, path in log_files.items():
        print(f"  • {log_type}: {path.name}")
    print()
    
    # Analyser les résultats
    main_log = log_files.get('run')
    if not main_log:
        print("❌ Fichier de log principal non trouvé!")
        return 1
        
    results = analyzer.parse_test_results(main_log)
    
    # Générer le rapport
    report = analyzer.generate_report(results)
    
    # Afficher ou sauvegarder
    if args.show:
        print(report)
    
    if args.output or not args.show:
        report_path = analyzer.save_report(report, args.output)
        print(f"📄 Rapport sauvegardé: {report_path}")
    
    return 0


if __name__ == "__main__":
    exit(main())
