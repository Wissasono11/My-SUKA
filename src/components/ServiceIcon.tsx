import type { ServiceId } from "@/lib/services";

const PATHS: Record<ServiceId, string> = {
  sukaketemu: "M11 4a7 7 0 105.2 11.7l3.4 3.4 1.4-1.4-3.4-3.4A7 7 0 0011 4zm0 2a5 5 0 110 10 5 5 0 010-10z",
  campusfix: "M14.7 6.3a4 4 0 00-5.4 5.1L3 17.7 6.3 21l6.3-6.3a4 4 0 005.1-5.4l-2.6 2.6-2.1-.5-.5-2.1 2.2-3z",
  siska: "M12 2l8 3v6c0 5-3.4 9.3-8 11-4.6-1.7-8-6-8-11V5l8-3zm0 2.1L6 6.4V11c0 3.8 2.4 7.2 6 8.8 3.6-1.6 6-5 6-8.8V6.4l-6-2.3zm-1 4.9h2v3h3v2h-3v3h-2v-3H8v-2h3z",
  archive: "M3 5a2 2 0 012-2h4l2 2h8a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2V5zm2 0v12h14V7h-8.8L8.2 5H5z",
  paas: "M5 3h14a2 2 0 012 2v10a2 2 0 01-2 2h-5v2h3v2H7v-2h3v-2H5a2 2 0 01-2-2V5a2 2 0 012-2zm0 2v10h14V5H5zm3 2h8v2H8V7zm0 3h5v2H8v-2z",
};

export default function ServiceIcon({ id, size = 28 }: { id: ServiceId; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false">
      <path fillRule="evenodd" d={PATHS[id]} />
    </svg>
  );
}
