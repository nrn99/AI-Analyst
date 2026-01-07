import os

from env_utils import resolve_gcp_project_id


def test_resolve_gcp_project_id_uses_google_cloud_project(monkeypatch):
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GCLOUD_PROJECT", raising=False)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "proj-123")

    project = resolve_gcp_project_id(set_env=True)

    assert project == "proj-123"
    assert os.getenv("GCP_PROJECT_ID") == "proj-123"


def test_resolve_gcp_project_id_prefers_gcp_project_id(monkeypatch):
    monkeypatch.setenv("GCP_PROJECT_ID", "proj-primary")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "proj-secondary")
    monkeypatch.delenv("GCLOUD_PROJECT", raising=False)

    project = resolve_gcp_project_id(set_env=True)

    assert project == "proj-primary"
