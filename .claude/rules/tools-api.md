---
paths:
  - "src/**/tools/**/*.py"
  - "src/wakastart_leads/shared/tools/**/*.py"
---

# Regles pour les Tools API

## Documentation des APIs

Les documentations API sont disponibles dans les dossiers tools :
- Pappers: `src/wakastart_leads/shared/tools/pappers_api.yaml`
- Kaspr: `src/wakastart_leads/crews/analysis/tools/kaspr_api.txt`
- Gamma: `src/wakastart_leads/crews/analysis/tools/gamma_api.txt`

## Tools disponibles

| Tool | Fichier | Utilise par |
|------|---------|-------------|
| PappersSearchTool | `shared/tools/pappers_tool.py` | Analysis, Search |
| KasprEnrichTool | `crews/analysis/tools/kaspr_tool.py` | Analysis |
| GammaCreateTool | `crews/analysis/tools/gamma_tool.py` | Analysis |

## Conventions de developpement

- Toujours heriter de `BaseTool` de CrewAI
- Implementer `_run()` comme methode principale
- Gerer les erreurs API avec try/except et retourner un message d'erreur explicite
- Logger tous les appels API dans les logs du crew
- Respecter les rate limits des APIs externes

## Variables d'environnement requises

```
PAPPERS_API_KEY   # Donnees legales entreprises
KASPR_API_KEY     # Enrichissement contacts
GAMMA_API_KEY     # Generation pages web
SERPER_API_KEY    # Recherche web
```

## Gestion des erreurs

- Retourner un dict avec `{"error": "message"}` en cas d'echec
- Ne jamais lever d'exception non geree
- Logger l'erreur avant de retourner
