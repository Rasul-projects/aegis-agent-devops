import os
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Core Environment Ingestion
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")
GITLAB_API_URL = os.getenv("GITLAB_API_URL", "https://gitlab.com/api/v4")

class AegisAgentEngine:
    def __init__(self):
        self.headers = {"Content-Type": "application/json"}
        self.gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"

    def parse_log_trace(self, raw_log_data: str) -> dict:
        """Isolates critical exception frames from noisy unstructured stack traces."""
        prompt = (
            f"Analyze this raw log data. Isolate the runtime error name, targeted file path, "
            f"and line number. Return ONLY a valid minified JSON object containing keys: "
            f"'error_type', 'file_path', and 'line_number'. Avoid any markdown or wrapper prose.\n\n{raw_log_data}"
        )
        
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            res = requests.post(self.gemini_url, headers=self.headers, json=payload, timeout=15)
            res.raise_for_status()
            clean_text = res.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            
            # Unpack markdown code blocks if the model appends them
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:-3].strip()
            elif clean_text.startswith("```"):
                clean_text = clean_text[3:-3].strip()
                
            return json.loads(clean_text)
        except Exception as e:
            return {"error": f"Log diagnostic isolation failed: {str(e)}"}

    def query_gitlab_mcp_context(self, project_id: str, file_path: str) -> str:
        """Executes context retrieval mapping into remote GitLab repositories."""
        if not GITLAB_TOKEN:
            return "Local fallback context enabled. Active token mapping missing."
            
        url = f"{GITLAB_API_URL}/projects/{project_id}/repository/files/{requests.utils.quote(file_path)}/raw?ref=main"
        headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}
        try:
            res = requests.get(url, headers=headers, timeout=10)
            return res.text if res.status_code == 200 else "Requested file matrix path not found on main branch."
        except Exception as e:
            return f"MCP bridging anomaly: {str(e)}"

    def generate_hotfix_patch(self, error_type: str, file_context: str, line: int) -> dict:
        """Executes multi-turn semantic reasoning loops to derive target source patches."""
        prompt = (
            f"Given a runtime system crash ('{error_type}') occurring at line {line}, "
            f"analyze the codebase contextual layer below and output a target hotfix code correction. "
            f"Return a clean JSON mapping with the keys 'root_cause' and 'proposed_patch'.\n\nCode Matrix:\n{file_context}"
        )
        
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            res = requests.post(self.gemini_url, headers=self.headers, json=payload, timeout=20)
            res.raise_for_status()
            clean_text = res.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:-3].strip()
            return json.loads(clean_text)
        except Exception as e:
            return {"error": f"Patch synthesis pipeline failure: {str(e)}"}

@app.route("/api/v1/diagnose", methods=["POST"])
def pipeline_entrypoint():
    payload = request.get_json() or {}
    logs = payload.get("logs")
    project_id = payload.get("project_id")

    if not logs or not project_id:
        return jsonify({"status": "error", "message": "Malformed payload criteria."}), 400

    agent = AegisAgentEngine()
    
    # 1. Parse log traces
    metrics = agent.parse_log_trace(logs)
    if "error" in metrics or "file_path" not in metrics:
        return jsonify({"status": "failed", "step": "parsing", "details": metrics}), 422

    # 2. Extract code context using Model Context Protocol (MCP) design pattern
    file_target = metrics["file_path"]
    codebase_context = agent.query_gitlab_mcp_context(project_id, file_target)

    # 3. Formulate resolution map
    patch_manifest = agent.generate_hotfix_patch(
        error_type=metrics["error_type"],
        file_context=codebase_context,
        line=metrics["line_number"]
    )

    return jsonify({
        "status": "success",
        "telemetry_analysis": metrics,
        "automated_remediation": patch_manifest
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
