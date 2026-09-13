#!/usr/bin/env python3
"""
WellnessHub — Diagnostic IA des échecs Jenkins
Utilise OpenAI GPT-4o-mini pour analyser les logs et générer un rapport
"""

import sys
import os
import json
import urllib.request
import urllib.error
from datetime import datetime


def analyze_failure(logs: str, stage: str, build_number: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return "ERREUR : Variable OPENAI_API_KEY non définie."

    prompt = f"""Tu es un expert DevOps spécialisé en Jenkins, Docker, AWS et Spring Boot.

Analyse le log d'échec Jenkins suivant et fournis un diagnostic structuré en français.

=== CONTEXTE ===
- Projet : WellnessHub (microservices Spring Boot + React)
- Build Jenkins : #{build_number}
- Étape en échec : {stage}
- Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}

=== LOG D'ERREUR ===
{logs[:3000]}

=== FORMAT DE RÉPONSE ATTENDU ===

🔴 CAUSE RACINE :
[Explique en 1-2 phrases la cause principale de l'échec]

🔍 ANALYSE DÉTAILLÉE :
[Explique ce qui s'est passé techniquement]

✅ ACTIONS CORRECTIVES :
1. [Action immédiate prioritaire]
2. [Action secondaire si applicable]
3. [Action préventive si applicable]

⚡ NIVEAU DE CRITICITÉ : [CRITIQUE / ÉLEVÉ / MOYEN / FAIBLE]

💡 CONSEIL :
[Un conseil technique pertinent pour éviter ce problème à l'avenir]
"""

    payload = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": "Tu es un expert DevOps. Analyse les logs Jenkins et fournis des diagnostics clairs et actionnables en français."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 800,
        "temperature": 0.3
    }).encode('utf-8')

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['choices'][0]['message']['content']
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        return f"ERREUR API OpenAI ({e.code}) : {error_body}"
    except Exception as e:
        return f"ERREUR inattendue : {str(e)}"


def main():
    if len(sys.argv) < 4:
        print("Usage: python3 ai_diagnostic.py <logs_file> <stage> <build_number>")
        sys.exit(1)

    logs_file = sys.argv[1]
    stage = sys.argv[2]
    build_number = sys.argv[3]

    try:
        with open(logs_file, 'r', encoding='utf-8', errors='ignore') as f:
            logs = f.read()
    except FileNotFoundError:
        logs = "Fichier de logs introuvable."

    if not logs.strip():
        logs = "Aucun log disponible."

    diagnostic = analyze_failure(logs, stage, build_number)
    print(diagnostic)


if __name__ == "__main__":
    main()
