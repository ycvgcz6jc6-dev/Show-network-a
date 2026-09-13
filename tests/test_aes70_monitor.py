from custom_components.dmx_monitor.aes70_monitor import AES70Record, _plain


def test_aes70_record_is_live_protocol_contract():
    row = AES70Record(
        host="10.0.0.10",
        port=65000,
        manufacturer="d&b audiotechnik",
        model="D40",
        device_name="PA-D40",
        serial="ABC123",
        device_role="amplifier",
        oca_version=4,
        state=1,
        roles=["Output1", "Output2"],
        online=True,
    ).snapshot()
    assert row["protocol"] == "AES70/OCA"
    assert row["manufacturer"] == "d&b audiotechnik"
    assert row["model"] == "D40"
    assert row["roles"] == ["Output1", "Output2"]
    assert row["online"] is True


def test_aes70_plain_handles_nested_values():
    assert _plain({"a": [1, b"\x01\xff"]}) == {"a": [1, "01ff"]}
