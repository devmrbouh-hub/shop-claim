"""WarGM client parser tests."""

from shop_claim_bridge.adapters.wargm_client import (
    WargmApiResponseError,
    _extract_operations_payload,
    check_wargm_envelope,
    parse_operation,
)
from fixtures.wargm_operations import (
    SAMPLE_OPERATIONS_LIST,
    SAMPLE_OPERATIONS_WRAPPED,
    SAMPLE_WARGM_ENVELOPE,
    SAMPLE_WARGM_V1_VERSION_ERROR,
    SAMPLE_WARGM_V11_ENVELOPE,
    SAMPLE_WARGM_V11_NESTED,
)


def test_parse_operation_list():
    row = SAMPLE_OPERATIONS_LIST[0]
    parsed = parse_operation(row)
    assert parsed is not None
    assert parsed["operation_id"] == "1001"
    assert parsed["offer_id"] == "5001"
    assert parsed["shop_server_id"] == 68109


def test_parse_wrapped_payload():
    rows = _extract_operations_payload(SAMPLE_OPERATIONS_WRAPPED)
    assert len(rows) == 1
    parsed = parse_operation(rows[0])
    assert parsed is not None
    assert parsed["operation_id"] == "1002"
    assert parsed["offer_id"] == "5002"


def test_parse_wargm_envelope_dict_data():
    rows = _extract_operations_payload(SAMPLE_WARGM_ENVELOPE)
    assert len(rows) == 1
    parsed = parse_operation(rows[0])
    assert parsed is not None
    assert parsed["operation_id"] == "7758693"
    assert parsed["offer_id"] == "264775"
    assert parsed["steam_id"] == "76561198000000001"
    assert parsed["shop_server_id"] == 10001


def test_parse_wargm_v11_envelope():
    rows = _extract_operations_payload(SAMPLE_WARGM_V11_ENVELOPE)
    assert len(rows) == 1
    parsed = parse_operation(rows[0])
    assert parsed is not None
    assert parsed["operation_id"] == "7758693"
    assert parsed["shop_server_id"] == 10001


def test_parse_wargm_v11_nested_operations():
    rows = _extract_operations_payload(SAMPLE_WARGM_V11_NESTED)
    assert len(rows) == 1
    parsed = parse_operation(rows[0])
    assert parsed is not None
    assert parsed["operation_id"] == "7758694"
    assert parsed["shop_server_id"] == 10001


def test_v1_version_error_raises():
    try:
        check_wargm_envelope(SAMPLE_WARGM_V1_VERSION_ERROR)
        assert False, "expected WargmApiResponseError"
    except WargmApiResponseError as exc:
        assert "not supported" in exc.message.lower()


def test_v1_version_error_extract_returns_empty():
    assert _extract_operations_payload(SAMPLE_WARGM_V1_VERSION_ERROR) == []
