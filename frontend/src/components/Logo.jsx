// Doc Decode mark: a folded page with a decoded line and a verification dot.
export default function Logo({ size = 22, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      className={className}
    >
      <path
        d="M7 3h13l5 5v19a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <path d="M20 3v5h5" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M9.5 15h9M9.5 19.5h6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="22.5" cy="23.5" r="3.5" fill="var(--accent, #4338ca)" />
      <path d="M21 23.5l1.1 1.1 2.1-2.2" stroke="#fff" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
