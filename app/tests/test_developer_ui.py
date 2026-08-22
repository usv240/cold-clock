from pathlib import Path
from service.main import app


def test_developer_console_is_visible_and_wired():
    web = Path(__file__).resolve().parents[1] / "web"
    html = (web / "index.html").read_text(encoding="utf-8")
    script = (web / "developer.js").read_text(encoding="utf-8")
    css = (web / "developer.css").read_text(encoding="utf-8")
    assert "Developer API · 50/day" in html
    assert "/api/developer/keys" in script
    assert "sessionStorage" in script
    assert ".developer-dialog" in css
    assert "/static/developer.js" in html and "/static/developer.css" in html


def test_openapi_marks_v1_as_api_key_protected():
    schema = app.openapi()
    assert schema["components"]["securitySchemes"]["DeveloperAPIKey"]["in"] == "header"
    v1 = [operation for path, methods in schema["paths"].items() if path.startswith("/v1") for operation in methods.values()]
    assert v1 and all({"DeveloperAPIKey": []} in operation.get("security", []) for operation in v1)

