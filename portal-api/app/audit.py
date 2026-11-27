"""Log audit keamanan: satu baris JSON per kejadian, TANPA data pribadi.

Hanya berisi nama kejadian, id layanan, alasan penolakan, id pengguna buram (usr_...) dan IP yang sudah dipotong
(/24 untuk IPv4, /56 untuk IPv6; sama dengan kebijakan Caddy). Tidak pernah memuat email, nama, NIM, kode, token, atau
rahasia. Dipakai untuk alert (lihat docs/RUNBOOK-KEAMANAN.md) dan penelusuran insiden.
"""
import ipaddress
import json
import logging

log = logging.getLogger("mysuka.audit")
_ALLOWED = {"service", "reason", "user", "ip", "sid_hash", "count"}


def mask_ip(ip: str | None) -> str:
    if not ip:
        return "-"
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return "-"
    prefix = 24 if addr.version == 4 else 56
    return str(ipaddress.ip_network(f"{addr}/{prefix}", strict=False))


def event(name: str, **fields: object) -> None:
    clean = {k: v for k, v in fields.items() if k in _ALLOWED and v is not None}
    log.info(json.dumps({"event": name, **clean}, separators=(",", ":"), sort_keys=True))
