#!/usr/bin/env python
import sys
import json
import os
from company_url_analysis_automation.crew import CompanyUrlAnalysisAutomationCrew

# This main file is intended to be a way for your to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information

def load_urls(test_mode=True):
    """Load URLs from JSON file. Use test_mode=True for liste_test.json (5 URLs), False for liste.json (976 URLs)."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    filename = 'liste_test.json' if test_mode else 'liste.json'
    json_path = os.path.join(project_root, filename)
    with open(json_path, 'r') as f:
        return json.load(f)

def run():
    """
    Run the crew.
    """
    urls = load_urls()
    inputs = {
        'urls': urls
    }
    CompanyUrlAnalysisAutomationCrew().crew().kickoff(inputs=inputs)


def train():
    """
    Train the crew for a given number of iterations.
    """
    urls = load_urls()
    inputs = {
        'urls': urls
    }
    try:
        CompanyUrlAnalysisAutomationCrew().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        CompanyUrlAnalysisAutomationCrew().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the results.
    """
    urls = load_urls()
    inputs = {
        'urls': urls
    }
    try:
        CompanyUrlAnalysisAutomationCrew().crew().test(n_iterations=int(sys.argv[1]), openai_model_name=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")

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
