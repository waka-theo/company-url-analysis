# Design : Optimisation Qualite/Prix WakaStart Leads

> Date: 2026-02-05
> Statut: Valide
> Auteur: Claude + Theo

## Contexte

Etude comparative pour optimiser le rapport qualite/prix du systeme WakaStart Leads sur 3 axes :
1. LLM Providers (Claude, Gemini, GPT)
2. Outils de Search/Scraping
3. Donnees entreprises (Pappers vs alternatives)

## Decisions

### 1. LLM Providers - Configuration optimisee

#### Configuration actuelle (100% GPT-4o)
| Agent | Modele | Cout/MTok |
|-------|--------|-----------|
| Tous les agents | GPT-4o | $6.25 |

#### Nouvelle configuration (mix optimise)
| Agent | Role | Nouveau modele | Cout/MTok | Justification |
|-------|------|----------------|-----------|---------------|
| **A3** | Ingenieur Commercial (scoring) | **Claude Sonnet 4.5** | $9.00 | Meilleur raisonnement business, scoring critique |
| **A4** | Gamma Creator | **Gemini 2.5 Pro** | $5.62 | Creatif, 2x moins cher que GPT-4o |
| **A1** | Intelligence Economique | **Gemini 2.5 Flash** | $1.40 | Extraction de donnees, pas besoin de premium |
| **A2** | Analyste Corporate | **Gemini 2.5 Flash** | $1.40 | Qualification SaaS, extraction |
| **A5** | Lead Generation | **Gemini 2.5 Flash** | $1.40 | Identification decideurs |
| **A6** | Data Compiler | **Gemini 2.0 Flash-Lite** | $0.19 | Formatage CSV simple |

#### Economies estimees
| Metrique | Avant | Apres | Economie |
|----------|-------|-------|----------|
| Cout moyen/100 URLs | ~$6.25 | ~$1.85 | **-70%** |
| Cout mensuel (500 URLs) | ~$31.25 | ~$9.25 | **-$22/mois** |

#### Tarifs de reference (fevrier 2026)

**Anthropic Claude** ([source](https://platform.claude.com/docs/fr/about-claude/pricing))
| Modele | Input/MTok | Output/MTok |
|--------|------------|-------------|
| Claude Opus 4.5 | $5.00 | $25.00 |
| Claude Sonnet 4.5 | $3.00 | $15.00 |
| Claude Haiku 4.5 | $1.00 | $5.00 |
| Claude Haiku 3 | $0.25 | $1.25 |

**Google Vertex AI Gemini** ([source](https://cloud.google.com/vertex-ai/generative-ai/pricing?hl=fr))
| Modele | Input/MTok | Output/MTok |
|--------|------------|-------------|
| Gemini 2.5 Pro | $1.25 | $10.00 |
| Gemini 2.5 Flash | $0.30 | $2.50 |
| Gemini 2.5 Flash Lite | $0.10 | $0.40 |
| Gemini 2.0 Flash | $0.15 | $0.60 |
| Gemini 2.0 Flash-Lite | $0.075 | $0.30 |

**OpenAI** ([source](https://openai.com/api/pricing/))
| Modele | Input/MTok | Output/MTok |
|--------|------------|-------------|
| GPT-5 | $1.25 | $10.00 |
| GPT-4o | $2.50 | $10.00 |
| GPT-4o-mini | $0.15 | $0.60 |

### 2. Outils Search/Scraping - Pas de changement

| Outil | Decision | Justification |
|-------|----------|---------------|
| **SerperDevTool** | ✅ Conserver | Bon rapport Q/P (~$1/1K req), integre CrewAI |
| **ScrapeWebsiteTool** | ✅ Conserver | Gratuit, suffisant pour sites corporate |

**Note** : Si volume > 10K URLs/mois, considerer Scrapingdog ($0.29/1K req).

### 3. Donnees Entreprises - Migration Pappers → API Sirene INSEE

#### Decision
Remplacer `PappersSearchTool` par un nouveau `SireneSearchTool` utilisant l'API gratuite de l'INSEE.

#### Comparatif
| Critere | Pappers | API Sirene INSEE |
|---------|---------|------------------|
| **Prix** | ~0.25€/requete | **Gratuit** |
| **SIREN/SIRET** | ✅ | ✅ |
| **Nom/Denomination** | ✅ | ✅ |
| **Date creation** | ✅ | ✅ |
| **Statut actif/cesse** | ✅ | ✅ |
| **Adresse siege** | ✅ | ✅ |
| **Effectif** | ✅ | ✅ |
| **Dirigeants** | ✅ | ❌ (Hunter les recupere) |
| **Chiffre affaires** | ✅ | ❌ (non critique) |

#### Economies
| Metrique | Pappers | Sirene | Economie |
|----------|---------|--------|----------|
| Cout/1000 URLs | ~250€ | 0€ | **-100%** |

#### Implementation requise
1. Creer compte sur [portail-api.insee.fr](https://portail-api.insee.fr/)
2. Souscrire a l'API Sirene V3.11
3. Creer `src/wakastart_leads/shared/tools/sirene_tool.py`
4. Mettre a jour les imports dans les crews

#### Endpoint API Sirene
```
Base URL: https://api.insee.fr/entreprises/sirene/V3.11

# Recherche par SIREN
GET /siren/{siren}

# Recherche par SIRET
GET /siret/{siret}

# Recherche multicritere
GET /siren?q=denominationUniteLegale:Google
```

## Resume des economies totales

| Poste | Avant | Apres | Economie |
|-------|-------|-------|----------|
| LLM (100 URLs) | $6.25 | $1.85 | -$4.40 (-70%) |
| Donnees entreprises (100 URLs) | ~$25 | $0 | -$25 (-100%) |
| Search/Scraping | ~$0.10 | ~$0.10 | $0 |
| **Total mensuel (500 URLs)** | **~$156** | **~$9.75** | **-$146 (-94%)** |

## Prochaines etapes

1. [ ] Creer compte INSEE et obtenir credentials API Sirene
2. [ ] Implementer `SireneSearchTool` (remplace `PappersSearchTool`)
3. [ ] Configurer Vertex AI pour Gemini (credentials Google Cloud)
4. [ ] Mettre a jour `crew.py` avec les nouveaux modeles LLM
5. [ ] Tester sur `liste_test.json` avant production
6. [ ] Mettre a jour CLAUDE.md avec la nouvelle architecture

## Risques et mitigations

| Risque | Impact | Mitigation |
|--------|--------|------------|
| Quotas API Sirene (30 req/min sans compte) | Moyen | Creer compte pour quotas eleves |
| Qualite Gemini Flash vs GPT-4o | Faible | Teste sur extraction, suffisant |
| Migration credentials Google Cloud | Faible | CrewAI supporte Vertex AI nativement |

## References

- [Tarifs Claude](https://platform.claude.com/docs/fr/about-claude/pricing)
- [Tarifs Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/pricing?hl=fr)
- [Tarifs OpenAI](https://openai.com/api/pricing/)
- [API Sirene INSEE](https://portail-api.insee.fr/)
- [Documentation Sirene](https://www.sirene.fr/sirene/public/static/documentation)
- [Comparatif SERP APIs](https://www.searchcans.com/blog/serp-api-pricing-index-2026/)
