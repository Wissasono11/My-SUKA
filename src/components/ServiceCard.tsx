import ServiceIcon from "./ServiceIcon";
import type { Service } from "@/lib/services";

export default function ServiceCard({ service, index }: { service: Service; index: number }) {
  return (
    <li className="card">
      <span className="card-icon"><ServiceIcon id={service.id} /></span>
      <span className="card-num" aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
      <h3>{service.title}</h3>
      <p>{service.description}</p>
      {/* Dibuka lewat launcher SSO agar masuk tanpa form login kedua. */}
      <a className="card-link" href={`/api/sso/launch?app=${service.id}`}>Buka {service.name}<span className="sr-only"> (masuk otomatis)</span></a>
    </li>
  );
}
