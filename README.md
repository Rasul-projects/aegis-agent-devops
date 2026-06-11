# Aegis Agent DevOps

An autonomous backend DevOps operations engine designed to accelerate incident response. Aegis Agent DevOps parses incoming system crash logs, securely retrieves repository context, and automatically generates targeted hotfix patches to dramatically reduce production downtime.

## System Architecture

The core engine is built on a high-speed Python backend using the Flask framework. The operational pipeline executes across three primary layers:

1. **Ingress Layer:** A Flask API endpoint actively listens for incoming raw, multi-line error payloads and unformatted system stack traces from logging services.
2. **Context Retrieval Layer:** The engine authenticates via fine-grained GitLab repository tokens to securely fetch the exact files and lines of code flagged by the system error.
3. **Reasoning & Patch Layer:** Utilizing the Gemini API with optimized raw header authentication, the tool evaluates the crash logs directly against the pulled source code context to generate ready-to-evaluate hotfix patches.

## Prerequisites

Before running the backend engine, ensure you have the following environment variables configured in your root directory:

* `GEMINI_API_KEY`: Your official Google Gemini API key used to authenticate reasoning tasks.
* `GITLAB_TOKEN`: A secure, fine-grained access token with read permissions for your project repositories.
* `GITLAB_API_URL`: (Optional) Defaults to the standard GitLab v4 API endpoint.

## Installation & Setup

1. Clone the project repository:
```bash
git clone [https://github.com/Rasul-projects/aegis-agent-devops.git](https://github.com/Rasul-projects/aegis-agent-devops.git)
cd aegis-agent-devops
