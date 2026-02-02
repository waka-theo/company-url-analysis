---
paths:
  - "tests/**/*.py"
  - "**/test_*.py"
  - "**/*_test.py"
---

# Conventions de Tests

## Structure des tests

```
tests/
├── conftest.py              # Fixtures partagees
├── crews/
│   ├── analysis/
│   │   ├── test_crew.py
│   │   └── tools/
│   ├── search/
│   └── enrichment/
└── shared/
    ├── tools/
    └── utils/
```

## Commandes pytest

```bash
pytest                           # Tous les tests
pytest tests/crews/analysis/     # Tests d'un crew specifique
pytest tests/shared/tools/       # Tests des tools partages
pytest -v                        # Mode verbose
pytest -x                        # Stopper au premier echec
pytest --tb=short                # Traceback court
```

## Conventions

- Utiliser `pytest` et `pytest-mock` pour les tests
- Mocker les appels API externes (Pappers, Kaspr, Gamma, Serper)
- Utiliser les fixtures de `conftest.py` pour les donnees de test
- Nommer les tests avec `test_<fonction>_<scenario>`

## Fichiers de test

- `liste_test.json` pour les URLs de test (pas `liste.json` en prod)
- Ne jamais committer de vraies cles API dans les tests
- Utiliser des mocks pour simuler les reponses API

## Assertions

- Toujours verifier le type de retour
- Verifier les cas limites (liste vide, URL invalide, etc.)
- Tester les cas d'erreur API
