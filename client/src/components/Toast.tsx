import { useCallback, useEffect, useRef, useState } from 'react';
import type { ToastItem } from './Toast.shared';

function ToastBubble({
  message,
  onDone,
}: {
  message: string;
  onDone: () => void;
}) {
  const [visible, setVisible] = useState(false);
  const onDoneRef = useRef(onDone);
  onDoneRef.current = onDone;

  useEffect(() => {
    // trigger enter animation on next frame
    const raf = requestAnimationFrame(() => setVisible(true));
    let exitTimer: ReturnType<typeof setTimeout> | undefined;
    const timer = setTimeout(() => {
      setVisible(false);
      // wait for exit animation before removing
      exitTimer = setTimeout(() => onDoneRef.current(), 300);
    }, 3000);
    return () => {
      cancelAnimationFrame(raf);
      clearTimeout(timer);
      if (exitTimer !== undefined) {
        clearTimeout(exitTimer);
      }
    };
  }, []);

  return (
    <div
      role='status'
      className={`pointer-events-auto flex items-center gap-2 rounded-2xl border border-white/70 bg-[rgba(255,255,255,0.92)] px-5 py-3 shadow-[0_12px_40px_rgba(11,33,33,0.12)] backdrop-blur-xl transition-all duration-300 ${
        visible ? 'translate-y-0 opacity-100' : 'translate-y-2 opacity-0'
      }`}
    >
      <span className='flex h-5 w-5 items-center justify-center rounded-full bg-[var(--color-accent)]'>
        <svg
          width='12'
          height='12'
          viewBox='0 0 24 24'
          fill='none'
          stroke='#fff'
          strokeWidth='3'
          strokeLinecap='round'
          strokeLinejoin='round'
        >
          <polyline points='20 6 9 17 4 12' />
        </svg>
      </span>
      <span className='text-sm font-medium text-[var(--color-text)]'>
        {message}
      </span>
    </div>
  );
}

export default function ToastContainer({
  toasts,
  onRemove,
}: {
  toasts: ToastItem[];
  onRemove: (id: number) => void;
}) {
  if (toasts.length === 0) return null;

  return (
    <div className='pointer-events-none fixed bottom-6 left-1/2 z-50 flex -translate-x-1/2 flex-col items-center gap-2'>
      {toasts.map((t) => (
        <ToastBubble
          key={t.id}
          message={t.message}
          onDone={() => onRemove(t.id)}
        />
      ))}
    </div>
  );
}
