"""Read GOLD daemon state and latest logs. 
Run on every user message during a scalping session.
Outputs: JSON with state type, title, body, and last 5 log entries."""
import json, os, subprocess

STATE_FILE = os.path.expanduser("~/AppData/Local/hermes/scripts/.gold_state.json")
LOG_FILE = os.path.expanduser("~/AppData/Local/hermes/scripts/.gold_manager.log")

result = {"state": None, "log_tail": []}

# Read state
if os.path.isfile(STATE_FILE):
    with open(STATE_FILE) as f:
        try:
            result["state"] = json.load(f)
        except:
            result["state"] = {"error": "corrupt"}

# Read last 5 log lines
if os.path.isfile(LOG_FILE):
    try:
        r = subprocess.run(["tail", "-5", LOG_FILE], capture_output=True, text=True, timeout=5)
        result["log_tail"] = [l for l in r.stdout.strip().split("\n") if l]
    except:
        result["log_tail"] = []

print(json.dumps(result, ensure_ascii=False))
