"""GOLD Notify Reader — забирает уведомления от демона и отправляет их в чат."""
import json, os

NOTIFY_FILE = os.path.join(os.path.dirname(__file__), '.gold_notify.json')

try:
    with open(NOTIFY_FILE, 'r') as f:
        notify = json.load(f)
    
    msg = notify.get("data", {}).get("msg", "")
    detail = notify.get("data", {}).get("detail", "")
    ntype = notify.get("type", "")
    
    if msg:
        output = msg
        if detail:
            output += f"\n{detail}"
        print(output)
    
    # Clear the notification
    with open(NOTIFY_FILE, 'w') as f:
        json.dump({"type": "none", "time": notify.get("time",""), "data": {}}, f)
        
except:
    pass  # silent if no notification
