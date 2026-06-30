"""Make aioice also gather a 127.0.0.1 host candidate for SmallWebRTCTransport.

Boxi's WebRTC voice path always runs browser and backend on the *same* machine
(this is a single-user local companion, not a hosted multi-client service). aioice
hardcodes excluding 127.0.0.1 from `get_host_addresses()` (it only targets real
interface IPs, the normal choice for cross-device calls). On a machine whose Wi-Fi
router has AP/client isolation enabled, UDP sent to the machine's own LAN-facing IP
gets silently dropped by the access point on the hairpin back, even though the
kernel routing table claims it goes via loopback — confirmed with a standalone
asyncio UDP repro independent of aiortc (P0-OSS-4 phase 3 verification,
2026-06-30): self-send via the LAN IP loses every packet with no error on either
end; the identical test via 127.0.0.1 delivers every packet. Offering 127.0.0.1 as
an *additional* server-side candidate (LAN-IP candidates stay too) gives ICE a pair
that works regardless of router/Wi-Fi network behavior, instead of depending on the
user disabling AP isolation on whatever network this machine happens to be on.
"""

from __future__ import annotations

import aioice.ice as _aioice_ice

_original_get_host_addresses = _aioice_ice.get_host_addresses


def _get_host_addresses_with_loopback(use_ipv4: bool, use_ipv6: bool) -> list[str]:
    addresses = _original_get_host_addresses(use_ipv4, use_ipv6)
    if use_ipv4 and "127.0.0.1" not in addresses:
        addresses.append("127.0.0.1")
    return addresses


def patch_aioice_loopback_candidate() -> None:
    """Idempotently patch aioice.ice.get_host_addresses to include 127.0.0.1."""
    if _aioice_ice.get_host_addresses is not _get_host_addresses_with_loopback:
        _aioice_ice.get_host_addresses = _get_host_addresses_with_loopback
