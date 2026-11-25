from dataclasses import dataclass


@dataclass(frozen=True)
class Service:
    id: str
    name: str
    href: str
    widget: bool  # SISKA dikecualikan demi kerahasiaan penyintas (kontrak 4.1)
    origin_env: str


SERVICES: tuple[Service, ...] = (
    Service("sukaketemu", "SukaKetemu", "/sukaketemu", True, "SUKAKETEMU_ORIGIN"),
    Service("campusfix", "CampusFix", "/campusfix", True, "CAMPUSFIX_ORIGIN"),
    Service("siska", "SISKA", "/siska", False, "SISKA_ORIGIN"),
    Service("archive", "Archive", "/archive", True, "ARCHIVE_ORIGIN"),
    Service("paas", "PaaS Praktikum", "/paas", True, "PAAS_ORIGIN"),
    Service("terassc", "TERAS SC", "/terassc", False, "TERASSC_ORIGIN"),
)


def get_service(service_id: str) -> Service | None:
    return next((s for s in SERVICES if s.id == service_id), None)
