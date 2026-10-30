export function BrandMark({ className = "" }: { className?: string }) {
  return (
    <svg className={`af-brand-symbol ${className}`} viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <path d="M5 25 14 6h4l9 19M9 18h14" stroke="currentColor" strokeWidth="2.5" strokeLinejoin="round" />
      <path d="M18 10h9v6h-5" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
