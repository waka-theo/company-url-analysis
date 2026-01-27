#!/usr/bin/env python
import csv
import io
import json
import os
import sys

from company_url_analysis_automation.crew import CompanyUrlAnalysisAutomationCrew

# This main file is intended to be a way for your to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information


def load_urls(test_mode=True):
    """Load URLs from JSON file. Use test_mode=True for liste_test.json (5 URLs), False for liste.json (976 URLs)."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    filename = "liste_test.json" if test_mode else "liste.json"
    json_path = os.path.join(project_root, filename)
    with open(json_path) as f:
        return json.load(f)


def post_process_csv(csv_path: str, expected_columns: int = 23):
    """
    Post-traitement du CSV genere par CrewAI :
    - Re-encode en UTF-8 BOM pour compatibilite Excel
    - Valide la structure (nombre de colonnes attendu)
    """
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    full_path = os.path.join(project_root, csv_path)

    if not os.path.exists(full_path):
        print(f"[WARNING] Fichier CSV non trouve : {full_path}")
        return

    with open(full_path, encoding="utf-8") as f:
        raw_content = f.read()

    if not raw_content.strip():
        print("[WARNING] CSV vide, pas de post-processing")
        return

    # Nettoyage des artefacts markdown (code fences, lignes vides)
    cleaned_lines = []
    for line in raw_content.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            continue
        if not stripped:
            continue
        cleaned_lines.append(line)
    raw_content = "\n".join(cleaned_lines)

    if not raw_content.strip():
        print("[WARNING] CSV vide apres nettoyage markdown, pas de post-processing")
        return

    reader = csv.reader(io.StringIO(raw_content))
    rows = list(reader)

    if not rows:
        print("[WARNING] CSV sans lignes, pas de post-processing")
        return

    validated_rows = []
    for i, row in enumerate(rows):
        if len(row) == expected_columns:
            validated_rows.append(row)
        elif len(row) > expected_columns:
            print(f"[WARNING] Ligne {i + 1}: {len(row)} colonnes (attendu {expected_columns}), troncature")
            validated_rows.append(row[:expected_columns])
        else:
            print(f"[WARNING] Ligne {i + 1}: {len(row)} colonnes (attendu {expected_columns}), completion")
            row.extend(["Non trouvé"] * (expected_columns - len(row)))
            validated_rows.append(row)

    with open(full_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerows(validated_rows)

    print(
        f"[OK] CSV post-traite : {len(validated_rows) - 1} entreprise(s), {expected_columns} colonnes, encodage UTF-8 BOM"
    )


def run():
    """
    Run the crew.
    """
    urls = load_urls()
    inputs = {"urls": urls}
    CompanyUrlAnalysisAutomationCrew().crew().kickoff(inputs=inputs)
    post_process_csv("output/company_report.csv")


def train():
    """
    Train the crew for a given number of iterations.
    """
    urls = load_urls()
    inputs = {"urls": urls}
    try:
        CompanyUrlAnalysisAutomationCrew().crew().train(
            n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs
        )

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}") from e


def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        CompanyUrlAnalysisAutomationCrew().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}") from e


def test():
    """
    Test the crew execution and returns the results.
    """
    urls = load_urls()
    inputs = {"urls": urls}
    try:
        CompanyUrlAnalysisAutomationCrew().crew().test(
            n_iterations=int(sys.argv[1]), openai_model_name=sys.argv[2], inputs=inputs
        )

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}") from e


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: main.py <command> [<args>]")
        sys.exit(1)

    command = sys.argv[1]
    if command == "run":
        run()
    elif command == "train":
        train()
    elif command == "replay":
        replay()
    elif command == "test":
        test()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
