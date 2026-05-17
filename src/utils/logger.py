import logging
import json

def log_agent_step(node_name: str, input_keys: list, output_keys: list, duration_ms: float):
    logging.info(json.dumps({
        "node": node_name,
        "input_keys": input_keys,
        "output_keys": output_keys,
        "duration_ms": round(duration_ms, 2)
    }))
