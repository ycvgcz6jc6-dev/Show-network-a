"""Reolink candidate RTSP URL construction in video_ip_supervision.py.

Covers the gap found while looking at the stream-sharing side of C21:
the mDNS-derived `uri` is only ever "rtsp://host:port" when the
advertisement itself carries no path property (common in practice), and
Reolink's real, documented stream path
(h264Preview_01_main/h265Preview_01_main, confirmed by Reolink's own
support article and cross-checked against a real reported Home
Assistant core issue showing the h264/h265 choice is genuinely
model-dependent) is never guessed at as a single "the" answer -- both
candidates are offered, clearly unverified.
"""
from __future__ import annotations

from custom_components.dmx_monitor.video_ip_supervision import VideoIPSupervision


def _mdns_row(*, host="10.4.2.30", port=554, vendor=None, name=None, path_prop=None, service_type="_rtsp._tcp.local."):
    props = {}
    if path_prop is not None:
        props["path"] = path_prop
    return {
        "service_type": service_type, "name": name, "host": host, "port": port,
        "vendor": vendor, "properties": props, "observed_at": 1000.0,
        "addresses": [host],
    }


def _endpoint(sup: VideoIPSupervision):
    rows = sup.snapshot()["endpoints"]
    assert len(rows) == 1
    return rows[0]


def test_reolink_with_no_path_gets_two_candidate_urls():
    sup = VideoIPSupervision()
    sup.observe_mdns(_mdns_row(vendor="Reolink RLC-810A", host="10.4.2.30", port=554))
    ep = _endpoint(sup)
    assert ep["uri"] == "rtsp://10.4.2.30"
    assert ep["candidate_stream_urls"] == [
        "rtsp://<username>:<password>@10.4.2.30/h264Preview_01_main",
        "rtsp://<username>:<password>@10.4.2.30/h265Preview_01_main",
    ]


def test_non_reolink_rtsp_device_gets_no_candidate_urls():
    """The whole point of scoping this to Reolink specifically: a
    generic/unknown RTSP camera's path convention isn't documented here
    at all, and this module must not invent one."""
    sup = VideoIPSupervision()
    sup.observe_mdns(_mdns_row(vendor="Axis Communications", host="10.4.2.31"))
    ep = _endpoint(sup)
    assert ep["candidate_stream_urls"] == []


def test_reolink_with_explicit_path_gets_no_guessed_candidates():
    """When the mDNS advertisement itself already gives a real path, the
    resulting `uri` is already trustworthy -- offering unverified guesses
    alongside a confirmed URI would be confusing, not helpful."""
    sup = VideoIPSupervision()
    sup.observe_mdns(_mdns_row(vendor="Reolink", host="10.4.2.30", path_prop="/h264Preview_01_main"))
    ep = _endpoint(sup)
    assert ep["uri"] == "rtsp://10.4.2.30/h264Preview_01_main"
    assert ep["candidate_stream_urls"] == []


def test_non_default_port_is_included_in_candidate_urls():
    sup = VideoIPSupervision()
    sup.observe_mdns(_mdns_row(vendor="Reolink", host="10.4.2.30", port=8554))
    ep = _endpoint(sup)
    assert ep["candidate_stream_urls"] == [
        "rtsp://<username>:<password>@10.4.2.30:8554/h264Preview_01_main",
        "rtsp://<username>:<password>@10.4.2.30:8554/h265Preview_01_main",
    ]


def test_never_opens_any_socket_to_probe_candidates():
    """This module's own file-level docstring states 'no sockets are
    opened to media endpoints' -- candidate construction is pure string
    building, never a connection attempt. Using a real unroutable
    address confirms observe_mdns() returns immediately either way,
    without hanging on any network call."""
    sup = VideoIPSupervision()
    result = sup.observe_mdns(_mdns_row(vendor="Reolink", host="192.0.2.50"))
    assert result is True
    ep = _endpoint(sup)
    assert "192.0.2.50" in ep["candidate_stream_urls"][0]


def test_reolink_marker_is_case_insensitive_and_can_appear_in_name():
    sup = VideoIPSupervision()
    sup.observe_mdns(_mdns_row(vendor=None, name="Backstage-REOLINK-Cam2", host="10.4.2.32"))
    ep = _endpoint(sup)
    assert len(ep["candidate_stream_urls"]) == 2
