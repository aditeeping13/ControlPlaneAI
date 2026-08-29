import json
import os
from datetime import datetime
from typing import Dict, Any

AUDIT_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'audit_log.json')

def log_audit(record: Dict[str, Any]):
    record["timestamp"] = datetime.utcnow().isoformat()
    
    logs = []
    if os.path.exists(AUDIT_FILE):
        try:
            with open(AUDIT_FILE, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        except Exception:
            pass
            
    logs.append(record)
    
    with open(AUDIT_FILE, 'w', encoding='utf-8') as f:
        json.dump(logs, f, indent=2)
