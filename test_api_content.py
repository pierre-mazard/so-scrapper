#!/usr/bin/env python3
"""Script pour tester la récupération du contenu via l'API Stack Overflow."""

import asyncio
import aiohttp
import json
from datetime import datetime

async def test_api_content():
    """Tester si l'API retourne le contenu des questions."""
    
    url = "https://api.stackexchange.com/2.3/questions"
    params = {
        'order': 'desc',
        'sort': 'creation',
        'site': 'stackoverflow',
        'page': 1,
        'pagesize': 3,  # Seulement 3 questions pour test
        'filter': 'withbody'  # Inclut le corps de la question
    }
    
    print("🔍 Test de récupération du contenu via API Stack Overflow")
    print("=" * 60)
    print(f"URL: {url}")
    print(f"Paramètres: {params}")
    print()
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    questions = data.get('items', [])
                    
                    print(f"📊 Réponse API reçue: {len(questions)} questions")
                    print(f"⏱️  Quota restant: {data.get('quota_remaining', 'N/A')}")
                    print()
                    
                    for i, q in enumerate(questions, 1):
                        print(f"📄 Question {i}:")
                        print(f"  • ID: {q.get('question_id', 'N/A')}")
                        print(f"  • Titre: {q.get('title', 'N/A')[:80]}...")
                        
                        # Vérifier la présence du body
                        body = q.get('body', '')
                        body_markdown = q.get('body_markdown', '')
                        
                        print(f"  • body (HTML): {'✅ Présent' if body else '❌ Absent'} ({len(body)} chars)")
                        print(f"  • body_markdown: {'✅ Présent' if body_markdown else '❌ Absent'} ({len(body_markdown)} chars)")
                        
                        if body:
                            print(f"    Extrait HTML: {body[:100]}...")
                        if body_markdown:
                            print(f"    Extrait Markdown: {body_markdown[:100]}...")
                        
                        print("    ---")
                    
                    # Afficher la structure complète de la première question
                    if questions:
                        print("\n🔍 STRUCTURE COMPLÈTE de la première question:")
                        print("=" * 50)
                        first_q = questions[0]
                        for key, value in first_q.items():
                            if isinstance(value, str) and len(value) > 100:
                                print(f"  {key}: {type(value).__name__} ({len(value)} chars)")
                            else:
                                print(f"  {key}: {value}")
                
                else:
                    print(f"❌ Erreur API: {response.status}")
                    print(f"Réponse: {await response.text()}")
                    
        except Exception as e:
            print(f"❌ Erreur lors de la requête: {e}")

if __name__ == "__main__":
    asyncio.run(test_api_content())
