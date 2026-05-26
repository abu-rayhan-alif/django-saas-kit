import json
import pytest

@pytest.mark.django_db
def test_schema_debug(api_client, settings):
    resp = api_client.get("/api/schema/?format=json")
    schema = json.loads(resp.content)
    token_post = schema["paths"]["/api/v1/auth/token/"]["post"]
    rb = token_post.get("requestBody", {})
    content_map = rb.get("content", {})
    json_content = content_map.get("application/json", {})
    print("DEBUG:", settings.DEBUG)
    print("json keys:", list(json_content.keys()))
    print("has examples:", "examples" in json_content)
