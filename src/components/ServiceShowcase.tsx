"use client";

import { useRef, useState } from "react";
import ServiceIcon from "@/components/ServiceIcon";
import { SERVICES } from "@/lib/services";

const featuredServices = SERVICES;
const initialIndex = Math.max(0, featuredServices.findIndex((service) => service.id === "siska"));

export default function ServiceShowcase() {
  const [activeIndex, setActiveIndex] = useState(initialIndex);
  const pointerStartX = useRef<number | null>(null);
  const count = featuredServices.length;

  const move = (direction: -1 | 1) => {
    setActiveIndex((current) => (current + direction + count) % count);
  };

  const goTo = (index: number) => {
    setActiveIndex((index + count) % count);
  };

  const activeService = featuredServices[activeIndex];

  return (
    <div
      className="service-stage"
      aria-label="Layanan digital MySuka"
      role="region"
      aria-roledescription="carousel"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === "ArrowLeft") {
          event.preventDefault();
          move(-1);
        } else if (event.key === "ArrowRight") {
          event.preventDefault();
          move(1);
        } else if (event.key === "Home") {
          event.preventDefault();
          goTo(0);
        } else if (event.key === "End") {
          event.preventDefault();
          goTo(count - 1);
        }
      }}
      onPointerDown={(event) => {
        pointerStartX.current = event.clientX;
      }}
      onPointerUp={(event) => {
        if (pointerStartX.current === null) return;
        const distance = event.clientX - pointerStartX.current;
        pointerStartX.current = null;
        if (Math.abs(distance) >= 45) move(distance > 0 ? -1 : 1);
      }}
      onPointerCancel={() => {
        pointerStartX.current = null;
      }}
    >
      <button className="stage-arrow stage-arrow-left" type="button" onClick={() => move(-1)} aria-label="Tampilkan layanan sebelumnya">
        <span aria-hidden="true">‹</span>
      </button>
      <ul className="service-showcase" aria-live="polite" aria-atomic="false">
        {featuredServices.map((service, index) => {
          let offset = (index - activeIndex + count) % count;
          if (offset > count / 2) offset -= count;
          const visible = Math.abs(offset) <= 2;
          const position = offset === 0 ? "center" : offset < 0 ? `left-${Math.abs(offset)}` : `right-${offset}`;
          const isActive = offset === 0;
          return (
            <li
              className={`showcase-card showcase-${position}${isActive ? " showcase-featured" : ""}${visible ? " is-visible" : " is-hidden"}`}
              key={service.id}
              aria-hidden={!visible}
              aria-label={`${index + 1} dari ${count}: ${service.name}`}
              role="group"
            >
              <span className="showcase-number">{String(index + 1).padStart(2, "0")}</span>
              <span className="showcase-icon"><ServiceIcon id={service.id} size={isActive ? 68 : 58} /></span>
              <h3>{service.title}</h3>
              <p>{service.description}</p>
              <a className="showcase-link" tabIndex={isActive ? 0 : -1} href={`/api/sso/launch?app=${service.id}`}>
                {service.name}<span className="sr-only"> (masuk otomatis)</span>
              </a>
            </li>
          );
        })}
      </ul>
      <button className="stage-arrow stage-arrow-right" type="button" onClick={() => move(1)} aria-label="Tampilkan layanan berikutnya">
        <span aria-hidden="true">›</span>
      </button>
      <div className="showcase-controls">
        <span className="showcase-counter" aria-live="polite">{String(activeIndex + 1).padStart(2, "0")} / {String(count).padStart(2, "0")}</span>
        <div className="showcase-dots" aria-label="Pilih layanan">
          {featuredServices.map((service, index) => (
            <button
              key={service.id}
              type="button"
              className={index === activeIndex ? "is-active" : ""}
              onClick={() => goTo(index)}
              aria-label={`Tampilkan ${service.name}${index === activeIndex ? ", layanan aktif" : ""}`}
              aria-current={index === activeIndex ? "true" : undefined}
            />
          ))}
        </div>
      </div>
      <span className="sr-only">Layanan aktif: {activeService.name}</span>
    </div>
  );
}
