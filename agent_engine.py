import os
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")
GITLAB_API_URL = os.getenv("GITLAB_API_URL", "[https://gitlab.com/api/v4](https://gitlab.com/api/v4)")

class AegisAgentEngine:
    def __init__(self):
        # Explicitly passing the API key via X-goog-api-key header format
        self.headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": GEMINI_API_KEY
        }
        self.gemini_url = "[https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent](https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent)"

    def clean_markdown_json(self, text: str) -> str:
        """Safely cleans out any markdown block formatting wrapper strings."""
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def parse_log_trace(self, raw_log_data: str) -> dict:
        prompt = (
            "Parse this raw log trace. Isolate the crash error type, target file path, "
            "and exact line number. Return ONLY a valid minified JSON object with keys: "
            "'error_type', 'file_path', and 'line_number'. No conversational prose.\n\n"
            f"Log Trace:\n{raw_log_data}"
        )
        
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            res = requests.post(self.gemini_url, headers=self.headers, json=payload, timeout=15)
            res.raise_for_status()
            raw_text = res.json()['candidates'][0]['content']['parts'][0]['text']
            
            # Use our bulletproof cleaner here
            clean_text = self.clean_markdown_json(raw_text)
            return json.loads(clean_text)
        except Exception as e:
            return {"error": f"Failed to parse log signature: {str(e)}"}

    def query_gitlab_mcp_context(self, project_id: str, file_path: str) -> str:
        if not GITLAB_TOKEN:
            return "Active GitLab routing token missing."
            
        url = f"{GITLAB_API_URL}/projects/{project_id}/repository/files/{requests.utils.quote(file_path)}/raw?ref=main"
        headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}
        try:
            res = requests.get(url, headers=headers, timeout=10)
            return res.text if res.status_code == 200 else "File path matrix resolve failure."
        except Exception as e:
            return f"MCP bridging exception: {str(e)}"

    def generate_hotfix_patch(self, error_type: str, file_context: str, line: int) -> dict:
        prompt = (
            f"A runtime exception ({error_type}) occurred on line {line}. "
            "Analyze the file context below, pinpoint the root vulnerability, and provide a patch. "
            "Return a clean JSON object using keys 'root_cause' and 'proposed_patch'.\n\n"
            f"Source Context:\n{file_context}"
        )
        
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            res = requests.post(self.gemini_url, headers=self.headers, json=payload, timeout=20)
            res.raise_for_status()
            raw_text = res.json()['candidates'][0]['content']['parts'][0]['text']
            
            clean_text = self.clean_markdown_json(raw_text)
            return json.loads(clean_text)
        except Exception as e:
            return {"error": f"Patch synthesis pipeline failure: {str(e)}"}

@app.route("/api/v1/diagnose", methods=["POST"])
def pipeline_entrypoint():
    payload = request.get_json() or {}
    logs = payload.get("logs")
    project_id = payload.get("project_id")

    if not logs or not project_id:
        return jsonify({"status": "error", "message": "Malformed payload params."}), 400

    agent = AegisAgentEngine()
    
    metrics = agent.parse_log_trace(logs)
    if "error" in metrics or "file_path" not in metrics:
        return jsonify({"status": "failed", "step": "parsing", "details": metrics}), 422

    file_target = metrics["file_path"]
    codebase_context = agent.query_gitlab_mcp_context(project_id, file_target)

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
