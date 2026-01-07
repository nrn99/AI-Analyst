#!/usr/bin/env python3
"""Startup checks for environment and dependencies.

This script reports missing env vars, credential path issues, region/bucket format,
and missing Python packages that commonly cause the runtime errors you saw.

It returns non-zero when run with `raise_on_error=True` inside CI or local checks.
"""
import os
import sys
import importlib
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # dotenv is optional; if not present, environment variables must be set externally
    pass

SUPPORTED_VERTEX_REGIONS = {
    "australia-southeast2","us-east7","europe-west3","australia-southeast1","asia-east2",
    "northamerica-northeast2","us-west1","europe-southwest1","europe-north1","us-central1",
    "us-east5","me-west1","northamerica-northeast1","me-central2","asia-south1","europe-west6",
    "us-west4","us-south1","europe-west9","europe-west12","us-east4","us-west3","asia-northeast2",
    "us-east1","asia-southeast1","africa-south1","asia-south2","southamerica-west1","europe-central2",
    "southamerica-east1","asia-southeast2","asia-east1","us-west2","europe-west1","asia-northeast1"
}


def _module_available(name: str) -> bool:
    try:
        importlib.import_module(name)
        return True
    except Exception:
        return False


def _version_of(package: str):
    try:
        from importlib.metadata import version
        return version(package)
    except Exception:
        try:
            import pkg_resources
            return pkg_resources.get_distribution(package).version
        except Exception:
            return None


def run_checks(raise_on_error: bool = True):
    errors = []
    warnings = []

    # Required env vars
    required_env = ["GCP_PROJECT_ID", "GOOGLE_APPLICATION_CREDENTIALS", "GCP_LOCATION", "STAGING_BUCKET"]
    for k in required_env:
        v = os.getenv(k)
        if not v:
            errors.append(f"Missing env var: {k}")

    # Credentials file existence
    cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if cred:
        cred = cred.strip()
        if not os.path.isabs(cred):
            # try to normalize relative paths
            cred = os.path.abspath(cred)
        if not os.path.isfile(cred):
            errors.append(f"GOOGLE_APPLICATION_CREDENTIALS file not found: {cred}")

    # staging bucket format
    bucket = os.getenv("STAGING_BUCKET", "")
    if bucket and not bucket.startswith("gs://"):
        errors.append(f"STAGING_BUCKET must start with gs:// (found: {bucket!r})")

    # region validation
    region = os.getenv("GCP_LOCATION") or os.getenv("AI_PLATFORM_LOCATION")
    if region:
        r = region.strip().strip('"\'"').strip()
        if r not in SUPPORTED_VERTEX_REGIONS:
            warnings.append(
                f"GCP_LOCATION {r!r} not in supported Vertex regions list; consider using one of {sorted(SUPPORTED_VERTEX_REGIONS)[:6]}..."
            )

    # module checks
    required_modules = [
        ("google.cloud.aiplatform", "google-cloud-aiplatform"),
        ("langchain", "langchain"),
        ("langchain_core", "langchain-core"),
        ("langchain_google_vertexai", "langchain-google-vertexai"),
    ]
    for mod, pkg in required_modules:
        if not _module_available(mod):
            errors.append(f"Missing Python module: {mod} (install package: {pkg})")
        else:
            v = _version_of(pkg)
            if v and pkg == "google-cloud-aiplatform":
                try:
                    from packaging.version import Version
                    if Version(v) < Version("1.112.0"):
                        warnings.append(f"{pkg} version {v} < 1.112.0 — upgrade to avoid region/agent issues")
                except Exception:
                    pass

    report = {"errors": errors, "warnings": warnings}
    if errors and raise_on_error:
        msg = "Startup checks failed:\n" + "\n".join(errors + warnings)
        raise SystemExit(msg)
    return report


def main():
    report = run_checks(raise_on_error=False)
    print("STARTUP CHECKS:")
    print("Errors:", report.get("errors"))
    print("Warnings:", report.get("warnings"))
    if report.get("errors"):
        # Provide uv-based remediation hints when modules are missing
        missing_pkgs = []
        for err in report.get("errors", []):
            if "Missing Python module:" in err:
                # extract package hint inside parentheses if present
                # format: Missing Python module: <mod> (install package: <pkg>)
                if "install package:" in err:
                    try:
                        pkg = err.split("install package:")[-1].strip().rstrip(')')
                        missing_pkgs.append(pkg)
                    except Exception:
                        pass

        if missing_pkgs:
            print("\nSuggested fix (using uv):")
            print("uv pip install " + " ".join(sorted(set(missing_pkgs))))
            print("or install requirements: uv pip install -r requirements.txt")

        sys.exit(2)


if __name__ == "__main__":
    main()
