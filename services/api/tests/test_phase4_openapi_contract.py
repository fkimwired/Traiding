from fable5_api.main import app


def _json_schema(operation: dict[str, object], status_code: str) -> dict[str, object]:
    responses = operation["responses"]
    assert isinstance(responses, dict)
    response = responses[status_code]
    assert isinstance(response, dict)
    content = response["content"]
    assert isinstance(content, dict)
    media_type = content["application/json"]
    assert isinstance(media_type, dict)
    schema = media_type["schema"]
    assert isinstance(schema, dict)
    return schema


def test_phase4_openapi_is_create_read_list_with_server_resolved_create_input() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    collection = paths["/v1/data-snapshots"]
    detail = paths["/v1/data-snapshots/{snapshot_id}"]

    assert set(collection) == {"get", "post"}
    assert set(detail) == {"get"}

    post = collection["post"]
    request_schema = post["requestBody"]["content"]["application/json"]["schema"]
    assert request_schema == {"$ref": "#/components/schemas/SnapshotCreateRequest"}
    assert _json_schema(post, "201") == {"$ref": "#/components/schemas/SnapshotBundle"}
    assert _json_schema(post, "422")["anyOf"] == [
        {"$ref": "#/components/schemas/SnapshotBuildBlockedResult"},
        {"$ref": "#/components/schemas/SnapshotRequestError"},
        {"$ref": "#/components/schemas/SnapshotValidationErrorResponse"},
    ]
    assert _json_schema(post, "503") == {"$ref": "#/components/schemas/AdapterUnavailableResult"}

    list_schema = _json_schema(collection["get"], "200")
    assert list_schema["type"] == "array"
    assert list_schema["items"] == {"$ref": "#/components/schemas/DataSnapshot"}
    assert _json_schema(detail["get"], "200") == {"$ref": "#/components/schemas/SnapshotBundle"}

    components = schema["components"]["schemas"]
    create = components["SnapshotCreateRequest"]
    assert create["additionalProperties"] is False
    assert set(create["properties"]) == {
        "mapping_id",
        "as_of_utc",
        "capability",
        "mock_configuration_id",
    }
    assert set(create["required"]) == set(create["properties"])


def test_phase4_generated_component_boundaries_are_closed_and_typed() -> None:
    components = app.openapi()["components"]["schemas"]

    assert components["DataCapability"]["enum"] == [
        "security_master",
        "universe_membership",
        "ohlcv",
        "corporate_actions",
        "delistings",
        "as_reported_fundamentals",
        "trading_calendar",
        "volatility_return_inputs",
        "official_document_event_metadata",
    ]
    for component_name in (
        "AdapterProfile",
        "SnapshotCreateRequest",
        "DataSnapshot",
        "SnapshotBundle",
        "AdapterUnavailableResult",
    ):
        assert components[component_name]["additionalProperties"] is False

    adapter_profile = components["AdapterProfile"]
    assert "synthetic" in adapter_profile["required"]
    assert adapter_profile["properties"]["synthetic"] == {
        "title": "Synthetic",
        "type": "boolean",
    }

    unavailable = components["AdapterUnavailableResult"]
    assert unavailable["properties"]["status"] == {
        "const": "unavailable",
        "default": "unavailable",
        "title": "Status",
        "type": "string",
    }
    assert unavailable["properties"]["sanitized_message"]["maxLength"] == 256

    bundle = components["SnapshotBundle"]
    assert set(bundle["required"]) == {
        "snapshot",
        "raw_observations",
        "normalized_observations",
        "revisions",
        "constituents",
        "quality_findings",
    }
