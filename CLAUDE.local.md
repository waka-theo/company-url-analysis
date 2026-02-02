# Preferences locales WakaStart

Ce fichier contient mes preferences personnelles pour ce projet (non partage avec l'equipe).

## Environnement de developpement

- Utiliser `liste_test.json` pour les tests, jamais `liste.json` en dev
- Environnement virtuel: `.venv/` (Python 3.10)
- IDE: Cursor

## Quotas API (a surveiller)

| API | Quota | Notes |
|-----|-------|-------|
| Pappers | Variable selon plan | Verifier le dashboard |
| Kaspr | ~100 req/heure | Rate limit strict |
| Gamma | Illimite (beta) | Peut changer |
| Serper | 2500 req/mois (free) | Surveiller usage |

## Raccourcis de dev

```bash
# Test rapide avec 2-3 URLs
python -m wakastart_leads.main run

# Debug verbose
PYTHONVERBOSE=1 python -m wakastart_leads.main run

# Test d'un crew specifique
pytest tests/crews/analysis/ -v
```

## Notes personnelles

- Le crew Search fonctionne mieux avec max_results <= 30
- Kaspr peut timeout sur les gros batches (> 50 contacts)
- Gamma genere parfois des pages avec des logos manquants (retry souvent)

## TODO personnel

- [ ] Optimiser le batch size pour Kaspr
- [ ] Ajouter un mode dry-run pour tester sans appels API
- [ ] Creer des fixtures pytest pour les reponses API
