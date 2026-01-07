import os

_METADATA_PROJECT_URL = "http://metadata.google.internal/computeMetadata/v1/project/project-id"
_METADATA_HEADERS = {"Metadata-Flavor": "Google"}


def _normalize_project_id(value):
    if not value:
        return None
    cleaned = value.strip().strip("'\"")
    return cleaned or None


def _seed_project_env(project_id):
    if not os.getenv("GCP_PROJECT_ID"):
        os.environ["GCP_PROJECT_ID"] = project_id
    if not os.getenv("GOOGLE_CLOUD_PROJECT"):
        os.environ["GOOGLE_CLOUD_PROJECT"] = project_id


def _project_id_from_metadata(timeout_seconds=0.2):
    # Cloud Run/Compute metadata server fallback.
    try:
        from urllib import request

        req = request.Request(_METADATA_PROJECT_URL, headers=_METADATA_HEADERS)
        with request.urlopen(req, timeout=timeout_seconds) as resp:
            return _normalize_project_id(resp.read().decode("utf-8"))
    except Exception:
        return None


def resolve_gcp_project_id(set_env=True):
    for env_name in ("GCP_PROJECT_ID", "GOOGLE_CLOUD_PROJECT", "GCLOUD_PROJECT"):
        project = _normalize_project_id(os.getenv(env_name))
        if project:
            if set_env:
                _seed_project_env(project)
            return project

    project = None
    try:
        import google.auth

        _, project = google.auth.default()
    except Exception:
        project = None

    project = _normalize_project_id(project)
    if not project:
        project = _project_id_from_metadata()

    if project and set_env:
        _seed_project_env(project)
    return project
