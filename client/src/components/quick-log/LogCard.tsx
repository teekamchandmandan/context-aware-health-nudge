import type { ReactNode } from 'react';

interface LogCardProps {
  eyebrow: string;
  title: string;
  children: ReactNode;
  apiError: string | null;
  className?: string;
}

export default function LogCard({
  eyebrow,
  title,
  children,
  apiError,
  className,
}: LogCardProps) {
  return (
    <section
      aria-label={`Log ${eyebrow.toLowerCase()}`}
      className={`flex flex-col rounded-[2rem] border border-white/70 bg-[rgba(255,255,255,0.82)] p-5 shadow-[0_24px_80px_rgba(11,33,33,0.08)] backdrop-blur-xl sm:p-6 ${className ?? ''}`}
    >
      <p className='text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-muted)]'>
        {eyebrow}
      </p>
      <h3 className='mt-1 font-headline text-lg font-bold tracking-[-0.04em] text-[var(--color-primary)]'>
        {title}
      </h3>

      {apiError && (
        <p
          role='alert'
          className='mt-3 rounded-[1rem] bg-[#fff0ee] px-4 py-3 text-sm font-medium text-[var(--color-error)]'
        >
          {apiError}
        </p>
      )}

      <div className='mt-4 flex flex-1 flex-col'>{children}</div>
    </section>
  );
}
