#!/usr/bin/env python
import json
import subprocess
import sys
import os
import logging
import time
import warnings

from datetime import datetime
from icecream import ic
import requests

from crew import CrewaiAgents
from dotenv import load_dotenv
load_dotenv()

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

TASK_API_URL = "http://localhost:8081/task/index/"  # API endpoint for SWE-Bench-Lite
TEST_API_URL = "http://localhost:8083/test/"  # API endpoint for SWE-Bench-Lite tests

REPOS_DIR = os.path.abspath("./repos") # Set this to the path of your repository if needed
LOGS_DIR = os.path.abspath("./logs")  # Set this to the path of your logs if needed
os.makedirs(REPOS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
file_handler = logging.FileHandler(os.path.join(LOGS_DIR, 'crewai_agents.log'))
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger = logging.getLogger(__name__)
logger.addHandler(file_handler)
logger.setLevel(logging.INFO)

# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information

def run_crew(repo:str="", task:str=""):
    """
    Run the crew.
    """
    inputs = {
        'repository': repo,
        'problem': task
    }

    try:
        crew = CrewaiAgents(working_directory=repo).crew(log_directory=LOGS_DIR)
        crew_output = crew.kickoff(inputs=inputs)
        
        try:
            logger.info(f"Usage Metrics: {crew.usage_metrics}")
        except Exception as e:
            logger.error(f"Error occurred while getting usage metrics: {e}")
        return crew_output
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"CrewAI LLM Exception: {e}")
        raise Exception(f"An error occurred while running the crew: {e}\n{tb}")


def handle_task(index):
    """
    Handle a specific task from the crew.
    """
    task_api_url = f"{TASK_API_URL}{index}"
    repo_dir = os.path.join(REPOS_DIR, f"repo_{index}")
    start_dir = os.getcwd() 
    
    # Fetch the task details from the API
    response = requests.get(task_api_url)
    if response.status_code != 200:
        raise Exception(f"Invalid Task API response: {response.status_code}")
    testcase = response.json()
    prompt = testcase["Problem_statement"]
    git_clone = testcase["git_clone"]
    fail_tests = json.loads(testcase.get("FAIL_TO_PASS", "[]"))
    pass_tests = json.loads(testcase.get("PASS_TO_PASS", "[]"))
    instance_id = testcase["instance_id"]
    parts = git_clone.split("&&")
    clone_part = parts[0].strip()
    checkout_part = parts[-1].strip() if len(parts) > 1 else None
    repo_url = clone_part.split()[2]
    commit_hash = checkout_part.split()[-1] if checkout_part else "main"
    
    # set up the repo directory
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    if not os.path.exists(repo_dir):
        subprocess.run(["git", "clone", repo_url, repo_dir], check=True, env=env)
    else:
        ic(f"Repo {repo_dir} already exists – skipping clone.")

    subprocess.run(["git", "checkout", commit_hash], cwd=repo_dir, check=True, env=env)
    
    # ___________________________________________
    # Run the crew
    try:
        if repo_dir and prompt: 
            ic(repo_dir, len(prompt))
        crew_output = run_crew(repo=repo_dir, task=prompt)
        try:
            logger.info(f"Token usage: {crew_output.token_usage}")
        except Exception as e:
            logger.error(f"Error occurred while getting usage metrics: {e}")
    except Exception as e:
        raise Exception(f"An error occurred while running crew in task: {e}")
    
    # __________________________________________
    # Run tests
    test_payload = {
        "instance_id": instance_id,
        "repoDir": f"/repos/repo_{index}",  # mount with docker
        "FAIL_TO_PASS": fail_tests,
        "PASS_TO_PASS": pass_tests
    }
    res = None
    try:
        res = requests.post("http://localhost:8083/test", json=test_payload)
        try:
            ic(res.status_code, res.text)
            res.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Error occurred while running tests: {e}")
            
        result_raw = res.json().get("harnessOutput", "{}")
        result_json = json.loads(result_raw)
        if not result_json:
            raise ValueError("No data in harnessOutput – possible evaluation error or empty result")
        instance_id = next(iter(result_json))
        tests_status = result_json[instance_id]["tests_status"]
        fail_pass_results = tests_status["FAIL_TO_PASS"]
        fail_pass_total = len(fail_pass_results["success"]) + len(fail_pass_results["failure"])
        fail_pass_passed = len(fail_pass_results["success"])
        pass_pass_results = tests_status["PASS_TO_PASS"]
        pass_pass_total = len(pass_pass_results["success"]) + len(pass_pass_results["failure"])
        pass_pass_passed = len(pass_pass_results["success"])
        os.chdir(start_dir)
        logger.info(f"FAIL_TO_PASS passed: {fail_pass_passed}/{fail_pass_total}\n")
        logger.info(f"PASS_TO_PASS passed: {pass_pass_passed}/{pass_pass_total}\n")
    except requests.RequestException as e:
        os.chdir(start_dir)
        logger.error(f"An error occurred while running tests: {e}")
        logger.error(f"Response content: {res if res else 'No response'}")
        

if  __name__ == "__main__":
    logger.info(f"Starting CrewaiAgents at {datetime.now().isoformat()}\n")
    
    for i in range(5, 31):
        logger.info(f"___ Task {i}  ___")
        try:
            handle_task(i)
            time.sleep(60)
        except Exception as e:
            print(f"An error occurred while handling task {i}: {e}")
            logger.error(f"An error occurred while handling task {i}: {e}")