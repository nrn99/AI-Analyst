import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import vertexai
from dotenv import load_dotenv
from vertexai.preview import reasoning_engines
from backend.processors.agent import FinanceAnalystAgent
from env_utils import resolve_gcp_project_id

def main():
    # 1. Load environment and CLEAN variables immediately
    load_dotenv(override=True)
    
    PROJECT_ID = resolve_gcp_project_id(set_env=True)
    LOCATION = os.getenv("GCP_LOCATION", "europe-west1").strip("'\"")
    STAGING_BUCKET = os.getenv("STAGING_BUCKET", "").strip("'\"")

    # Force print these out so we know EXACTLY what Python sees
    print(f"--- Environment Diagnostic ---", flush=True)
    print(f"Project: [{PROJECT_ID}]", flush=True)
    print(f"Bucket:  [{STAGING_BUCKET}]", flush=True)
    
    if not PROJECT_ID:
        print("❌ ERROR: GCP_PROJECT_ID (or GOOGLE_CLOUD_PROJECT) could not be resolved", flush=True)
        return

    if not STAGING_BUCKET.startswith("gs://"):
        print("❌ ERROR: STAGING_BUCKET is empty or missing 'gs://'", flush=True)
        return

    # 2. INITIALIZE FIRST (This must happen before any other vertexai calls)
    vertexai.init(
        project=PROJECT_ID, 
        location=LOCATION, 
        staging_bucket=STAGING_BUCKET
    )

    # 3. Local Test (Optional)
    print("\n--- Running Local Test ---", flush=True)
    # tester = FinanceAnalystAgent()
    # tester.set_up()
    # print(f"Response: {tester.query('Jag köpte kaffe för 30kr.')}")

    # 4. Deployment (Removed the 'staging_bucket' argument to fix TypeError)
    print("\n--- Deploying to Vertex AI Agent Engine ---", flush=True)
    
    # We create a FRESH instance here
    agent_instance = FinanceAnalystAgent()

    remote_agent = reasoning_engines.ReasoningEngine.create(
        agent_instance,
        display_name="Finance_Agent_v3",
        requirements=[
            "google-cloud-aiplatform[agent_engines]",
            "langchain-google-genai",
            "langchain-classic",
            "langchain-core",
            "google-api-python-client",
            "google-auth-httplib2",
            "google-auth-oauthlib",
            "python-dotenv"
        ],
        extra_packages=["env_utils.py", "backend"]
    )

    print(f"\n✅ SUCCESS! Agent live at: {remote_agent.resource_name}", flush=True)

if __name__ == "__main__":
    main()
