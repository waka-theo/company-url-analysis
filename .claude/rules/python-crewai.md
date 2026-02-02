---
paths:
  - "src/**/*.py"
---

# Conventions Python & CrewAI

## Structure des Agents

- Chaque agent doit avoir un `role`, `goal`, et `backstory` explicites dans `agents.yaml`
- Les temperatures sont definies dans `agents.yaml`, les modeles LLM dans `crew.py`
- Utiliser les decorateurs `@agent` et `@task` de CrewAI

## Architecture des Crews

| Crew | Agents | Modele principal |
|------|--------|------------------|
| Analysis | 6 agents | Mix GPT-4o + Claude Sonnet |
| Search | 1 agent | Claude Sonnet |
| Enrichment | 1 agent | GPT-4o |

## Imports et Organisation

- Toujours importer depuis `wakastart_leads.shared.utils` pour les utilitaires
- Ne jamais dupliquer les utilitaires entre crews
- Utiliser `constants.py` pour tous les chemins de fichiers

## Conventions de Code

- Typage explicite pour toutes les fonctions (pas de `Any`)
- Docstrings en francais pour les fonctions publiques
- Gestion d'erreurs avec try/except et logging approprie

## Logging

- Utiliser le module `log_rotation.py` pour les logs
- Format: `run_YYYYMMDD_HHMMSS.json` dans le dossier `output/logs/` de chaque crew
- Rotation automatique des logs > 30 jours
