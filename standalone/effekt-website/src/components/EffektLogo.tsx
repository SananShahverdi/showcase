type EffektLogoProps = {
  compact?: boolean;
  className?: string;
};

function EffektSymbol({ compact = false }: { compact?: boolean }) {
  return (
    <g fill="none" stroke="currentColor">
      <rect x="6" y="6" width="52" height="52" strokeWidth="3" />
      <path
        d="M20 6h24l14 14v24L44 58H20L6 44V20L20 6Z"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <circle cx="32" cy="32" r="14" strokeWidth="2.5" />
      <circle cx="32" cy="32" r="4" fill="currentColor" stroke="none" />
      {!compact && (
        <>
          <path d="M32 2v10M32 52v10" strokeWidth="2.5" />
          <path d="M2 32h10M52 32h10" strokeWidth="2.5" />
        </>
      )}
    </g>
  );
}

export function EffektLogo({
  compact = false,
  className,
}: EffektLogoProps) {
  if (compact) {
    return (
      <svg
        className={className}
        viewBox="0 0 64 64"
        role="img"
        aria-label="Effekt"
      >
        <EffektSymbol compact />
      </svg>
    );
  }

  return (
    <svg
      className={className}
      viewBox="0 0 238 64"
      role="img"
      aria-label="Effekt"
    >
      <EffektSymbol />
      <g fill="currentColor">
        <path d="M78 18h20v5H84v6h11v5H84v7h14v5H78V18Z" />
        <path d="M104 18h20v5h-14v6h11v5h-11v12h-6V18Z" />
        <path d="M128 18h20v5h-14v6h11v5h-11v12h-6V18Z" />
        <path d="M152 18h20v5h-14v6h11v5h-11v7h14v5h-20V18Z" />
        <path d="M178 18h6v11l12-11h8l-12 12 13 16h-8l-10-12-3 3v9h-6V18Z" />
        <path d="M208 18h22v5h-8v23h-6V23h-8v-5Z" />
      </g>
    </svg>
  );
}
