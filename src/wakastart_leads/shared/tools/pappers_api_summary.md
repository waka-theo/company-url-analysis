# API Pappers - Resume (endpoints utilises dans le projet)

Base URL: `https://api.pappers.fr/v2`
Auth: Header `api-key: <PAPPERS_API_KEY>`

## Endpoints utilises

### 1. GET /entreprise - Fiche entreprise par SIREN

```
GET /entreprise?siren=443061841
```

**Reponse principale:**
- `siren`, `siret` (siege)
- `nom_entreprise`, `denomination`
- `forme_juridique`, `date_creation`
- `entreprise_cessee` (boolean)
- `code_naf`, `libelle_code_naf`
- `effectif`, `capital`
- `siege.adresse_ligne_1`, `siege.code_postal`, `siege.ville`
- `representants[]` - Liste des dirigeants (nom_complet, qualite)
- `beneficiaires_effectifs[]` - (prenom, nom, pourcentage_parts)
- `finances` - (chiffre_affaires, resultat)

### 2. GET /recherche - Recherche par nom

```
GET /recherche?q=Google&par_page=5&cibles=nom_entreprise,denomination
```

**Reponse:**
- `resultats[]` ou `resultats_nom_entreprise[]`
  - `siren`, `nom_entreprise`, `denomination`
  - `date_creation`
  - `siege.ville`

## Codes erreur

| Code | Signification |
|------|---------------|
| 200 | Succes |
| 401 | Cle API invalide |
| 404 | Entreprise non trouvee |

## Documentation complete

Pour la spec OpenAPI complete (336k chars), voir:
`src/wakastart_leads/shared/tools/pappers_api.yaml`
