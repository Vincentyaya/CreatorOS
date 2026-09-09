type P = { className?: string }

const base = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.6,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  viewBox: "0 0 24 24",
}

export const Radar = ({ className }: P) => (
  <svg {...base} className={className}>
    <circle cx="12" cy="12" r="9" />
    <circle cx="12" cy="12" r="5" />
    <path d="M12 12 20 6" />
    <circle cx="16" cy="9" r="1" fill="currentColor" stroke="none" />
  </svg>
)

export const Scan = ({ className }: P) => (
  <svg {...base} className={className}>
    <path d="M4 8V6a2 2 0 0 1 2-2h2M16 4h2a2 2 0 0 1 2 2v2M20 16v2a2 2 0 0 1-2 2h-2M8 20H6a2 2 0 0 1-2-2v-2" />
    <path d="M4 12h16" />
  </svg>
)

export const Book = ({ className }: P) => (
  <svg {...base} className={className}>
    <path d="M4 5a2 2 0 0 1 2-2h11a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H6a2 2 0 0 0-2 2z" />
    <path d="M4 19a2 2 0 0 1 2-2h12" />
  </svg>
)

export const Sparkle = ({ className }: P) => (
  <svg {...base} className={className}>
    <path d="M12 3v4M12 17v4M3 12h4M17 12h4" />
    <path d="M12 8.5 13.2 11 15.5 12l-2.3 1L12 15.5 10.8 13 8.5 12l2.3-1z" />
  </svg>
)

export const Chart = ({ className }: P) => (
  <svg {...base} className={className}>
    <path d="M4 20V4" />
    <path d="M4 20h16" />
    <path d="M8 16v-3M12 16V9M16 16v-6" />
  </svg>
)

export const Arrow = ({ className }: P) => (
  <svg {...base} className={className}>
    <path d="M5 12h14M13 6l6 6-6 6" />
  </svg>
)

export const Play = ({ className }: P) => (
  <svg {...base} className={className}>
    <circle cx="12" cy="12" r="9" />
    <path d="M10 9l5 3-5 3z" fill="currentColor" stroke="none" />
  </svg>
)

export const Up = ({ className }: P) => (
  <svg {...base} className={className}>
    <path d="M6 15l6-6 6 6" />
  </svg>
)

export const Check = ({ className }: P) => (
  <svg {...base} className={className}>
    <path d="M5 12l4 4 10-10" />
  </svg>
)

export const Ban = ({ className }: P) => (
  <svg {...base} className={className}>
    <circle cx="12" cy="12" r="9" />
    <path d="M6 6l12 12" />
  </svg>
)

export const Link = ({ className }: P) => (
  <svg {...base} className={className}>
    <path d="M10 14a4 4 0 0 0 6 .5l2-2a4 4 0 0 0-6-6l-1 1" />
    <path d="M14 10a4 4 0 0 0-6-.5l-2 2a4 4 0 0 0 6 6l1-1" />
  </svg>
)

export const Upload = ({ className }: P) => (
  <svg {...base} className={className}>
    <path d="M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" />
    <path d="M12 4v12M7 9l5-5 5 5" />
  </svg>
)

export const Eye = ({ className }: P) => (
  <svg {...base} className={className}>
    <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
)

export const EyeOff = ({ className }: P) => (
  <svg {...base} className={className}>
    <path d="M10.6 6.2A9.7 9.7 0 0 1 12 6c6.5 0 10 6 10 6a15.6 15.6 0 0 1-3.2 3.8M6.2 6.6A15.5 15.5 0 0 0 2 12s3.5 6 10 6a9.6 9.6 0 0 0 4.1-.9" />
    <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" />
    <path d="M3 3l18 18" />
  </svg>
)

export const Dot = ({ className }: P) => (
  <svg viewBox="0 0 8 8" className={className}>
    <circle cx="4" cy="4" r="4" fill="currentColor" />
  </svg>
)
