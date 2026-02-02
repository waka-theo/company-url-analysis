---
paths:
  - "src/**/csv_utils.py"
  - "src/**/crew.py"
  - "**/*report*.py"
---

# Format CSV de Sortie

## Fichier principal

`crews/analysis/output/company_report.csv` (UTF-8 BOM, 23 colonnes)

## Structure des colonnes

| Col | Nom | Type | Description |
|-----|-----|------|-------------|
| A | Societe | string | Nom commercial de l'entreprise |
| B | Site Web | URL | URL racine du site |
| C | Nationalite | enum | FR, INT, US, UK, DE, etc. |
| D | Annee Creation | YYYY | Annee de creation |
| E | Solution SaaS | string | Description courte (max 20 mots) |
| F | Pertinence (%) | 0-100 | Score de pertinence WakaStart |
| G | Strategie & Angle | string | Angle commercial recommande |
| H | Decideur 1 - Nom | string | Nom complet |
| I | Decideur 1 - Titre | string | Poste/fonction |
| J | Decideur 1 - Email | email | Email professionnel |
| K | Decideur 1 - Telephone | phone | Numero de telephone |
| L | Decideur 1 - LinkedIn | URL | Profil LinkedIn |
| M-Q | Decideur 2 | ... | Meme structure |
| R-V | Decideur 3 | ... | Meme structure |
| W | Page Gamma | URL | URL de la page Gamma generee |

## Conventions

- Encodage: UTF-8 avec BOM pour Excel
- Separateur: virgule (,)
- Guillemets: doubles (") pour les champs contenant des virgules
- Pas de lignes vides entre les enregistrements

## Post-traitement

Utiliser `csv_utils.py` pour :
- `load_existing_csv()` - Charger un CSV existant
- `post_process_csv()` - Nettoyer et formater
- `clean_markdown_artifacts()` - Supprimer les artefacts markdown
