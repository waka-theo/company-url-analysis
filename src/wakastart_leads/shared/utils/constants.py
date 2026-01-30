"""Constantes partagees du projet."""

from pathlib import Path

# Racine du package
PACKAGE_ROOT = Path(__file__).parent.parent.parent

# Chemins des crews
ANALYSIS_DIR = PACKAGE_ROOT / "crews" / "analysis"
SEARCH_DIR = PACKAGE_ROOT / "crews" / "search"
ENRICHMENT_DIR = PACKAGE_ROOT / "crews" / "enrichment"

# Chemins input/output par crew
ANALYSIS_INPUT = ANALYSIS_DIR / "input"
ANALYSIS_OUTPUT = ANALYSIS_DIR / "output"
SEARCH_INPUT = SEARCH_DIR / "input"
SEARCH_OUTPUT = SEARCH_DIR / "output"
ENRICHMENT_INPUT = ENRICHMENT_DIR / "input"
ENRICHMENT_OUTPUT = ENRICHMENT_DIR / "output"

# Fichiers par defaut
ANALYSIS_CSV_FINAL = ANALYSIS_OUTPUT / "company_report.csv"
ANALYSIS_CSV_NEW = ANALYSIS_OUTPUT / "company_report_new.csv"
SEARCH_RAW_OUTPUT = SEARCH_OUTPUT / "search_results_raw.json"
ENRICHMENT_ACCUMULATED = ENRICHMENT_OUTPUT / "enrichment_accumulated.json"

# Configuration
EXPECTED_COLUMNS = 23
URL_COLUMN_INDEX = 1
DEFAULT_BATCH_SIZE = 20
