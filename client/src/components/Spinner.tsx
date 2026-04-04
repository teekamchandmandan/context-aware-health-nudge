export default function Spinner() {
  return (
    <div className='flex justify-center py-8 sm:py-12'>
      <div className='rounded-[1.75rem] border border-white/80 bg-[rgba(255,255,255,0.82)] px-8 py-10 text-center shadow-[0_18px_55px_rgba(25,28,29,0.05)]'>
        <div className='relative mx-auto h-12 w-12' role='status'>
          <div className='absolute inset-0 rounded-full border-[3px] border-[rgba(168,239,239,0.45)]' />
          <div className='absolute inset-0 animate-spin rounded-full border-[3px] border-[var(--color-primary)] border-t-transparent' />
          <span className='sr-only'>Loading…</span>
        </div>
        <p className='mt-4 font-headline text-xl font-bold tracking-[-0.03em] text-[var(--color-primary)]'>
          Loading your update
        </p>
        <p className='mt-2 text-sm text-[var(--color-muted)]'>
          Getting things ready for you.
        </p>
      </div>
    </div>
  );
}
