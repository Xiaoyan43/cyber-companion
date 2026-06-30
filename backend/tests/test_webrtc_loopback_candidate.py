import aioice.ice as aioice_ice

from backend.realtime.webrtc_loopback_candidate import patch_aioice_loopback_candidate


def test_patch_adds_loopback_candidate(monkeypatch) -> None:
    def fake_get_host_addresses(use_ipv4: bool, use_ipv6: bool) -> list[str]:
        return ["192.168.1.23"] if use_ipv4 else []

    monkeypatch.setattr(
        "backend.realtime.webrtc_loopback_candidate._original_get_host_addresses",
        fake_get_host_addresses,
    )
    monkeypatch.setattr(aioice_ice, "get_host_addresses", fake_get_host_addresses)

    patch_aioice_loopback_candidate()

    assert aioice_ice.get_host_addresses(use_ipv4=True, use_ipv6=False) == [
        "192.168.1.23",
        "127.0.0.1",
    ]


def test_patch_is_idempotent(monkeypatch) -> None:
    def fake_get_host_addresses(use_ipv4: bool, use_ipv6: bool) -> list[str]:
        return ["192.168.1.23"] if use_ipv4 else []

    monkeypatch.setattr(
        "backend.realtime.webrtc_loopback_candidate._original_get_host_addresses",
        fake_get_host_addresses,
    )
    monkeypatch.setattr(aioice_ice, "get_host_addresses", fake_get_host_addresses)

    patch_aioice_loopback_candidate()
    patch_aioice_loopback_candidate()

    addresses = aioice_ice.get_host_addresses(use_ipv4=True, use_ipv6=False)
    assert addresses.count("127.0.0.1") == 1


def test_patch_skips_loopback_when_ipv4_disabled(monkeypatch) -> None:
    def fake_get_host_addresses(use_ipv4: bool, use_ipv6: bool) -> list[str]:
        return []

    monkeypatch.setattr(
        "backend.realtime.webrtc_loopback_candidate._original_get_host_addresses",
        fake_get_host_addresses,
    )
    monkeypatch.setattr(aioice_ice, "get_host_addresses", fake_get_host_addresses)

    patch_aioice_loopback_candidate()

    assert aioice_ice.get_host_addresses(use_ipv4=False, use_ipv6=True) == []
