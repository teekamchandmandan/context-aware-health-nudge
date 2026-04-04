interface Props {
  message: string;
  onRetry: () => void;
}

export default function SectionError({ message, onRetry }: Props) {
  return (
    <div className='rounded-[1.75rem] border border-[#f0c6c1] bg-[linear-gradient(180deg,rgba(255,255,255,0.95),rgba(255,240,238,0.92))] p-6 text-center shadow-[0_18px_55px_rgba(25,28,29,0.05)]'>
      <p className='font-headline text-2xl font-bold tracking-[-0.03em] text-[var(--color-primary)]'>
        Something went wrong.
      </p>
      <p className='mx-auto mt-3 max-w-xl text-sm leading-7 text-[var(--color-muted)]'>
        {message}
      </p>
      <button
        onClick={onRetry}
        className='mt-5 inline-flex items-center justify-center rounded-[1rem] bg-[var(--color-primary)] px-5 py-3 text-sm font-semibold text-white shadow-[0_16px_36px_rgba(0,66,66,0.18)] transition hover:-translate-y-0.5 hover:bg-[var(--color-primary-strong)]'
      >
        Try again
      </button>
    </div>
  );
}
