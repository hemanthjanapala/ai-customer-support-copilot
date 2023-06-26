import sys
import importlib.metadata
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

def check_version(package_name, expected_substring):
    try:
        version = importlib.metadata.version(package_name)
        status = "✅ PASS" if expected_substring in version else f"⚠️ CHECK (Found {version})"
        print(f"[{status}] {package_name}: {version} (Expected: {expected_substring})")
    except importlib.metadata.PackageNotFoundError:
        print(f"[❌ FAIL] {package_name}: Not installed")

def main():
    print("=== Stack & Dependency Verification ===")
    print(f"Python Version: {sys.version.split()[0]} (Target: ~3.11)")

    # 1 & 5. Check Pydantic & Pydantic Settings
    check_version("pydantic", "2.")
    check_version("pydantic-settings", "2.")

    # 2. Check OpenAI SDK version
    check_version("openai", "0.28")

    # Check FastAPI & Uvicorn
    check_version("fastapi", "0.1")
    check_version("uvicorn", "0.")

    print("\n=== Configuration & Model Check ===")
    print(f"Configured OpenAI Model: {settings.openai_model}")
    if settings.openai_model in ["gpt-3.5-turbo", "gpt-4"]:
        print("✅ PASS: Model aligns with mid-2023 options.")
    else:
        print(f"⚠️ WARNING: Model '{settings.OPENAI_MODEL}' is newer than mid-2023 options.")

    print("\n=== Live Application Sanity Check ===")
    try:
        client = TestClient(app)
        # Adjust endpoint path if your health check or root is different
        response = client.get("/")
        print(f"✅ PASS: FastAPI app booted successfully (Root endpoint status code: {response.status_code})")
    except Exception as e:
        print(f"❌ FAIL: FastAPI app failed to respond to test client: {e}")

if __name__ == "__main__":
    main()