import { useEffect, useRef, useState } from 'react';
import type { NudgeDetail, ActionType } from '../types/member';
import { postAction, ApiError } from '../api/client';
import { formatTimestamp } from '../utils/formatTimestamp';

interface Props {
  nudge: NudgeDetail;
  onActionComplete: () => void;
}

const ACTION_CONFIRMATIONS: Record<ActionType, string> = {
  act_now: 'Thanks. We will check in again soon.',
  dismiss: 'Okay. We will leave it here for now.',
  ask_for_help: 'Thanks. Someone from your care team will follow up.',
};

const ACTION_ERROR_MESSAGE = 'We could not save that. Please try again.';

export default function NudgeCard({ nudge, onActionComplete }: Props) {
  const [acting, setActing] = useState<ActionType | null>(null);
  const [confirmation, setConfirmation] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const confirmationTimerRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );

  useEffect(() => {
    return () => {
      if (confirmationTimerRef.current !== null) {
        clearTimeout(confirmationTimerRef.current);
      }
    };
  }, []);

  function getActionErrorMessage(err: unknown): string {
    if (err instanceof ApiError && err.status === 404) {
      console.error('Nudge action endpoint returned 404', err.body);
    }

    return ACTION_ERROR_MESSAGE;
  }

  async function handleAction(actionType: ActionType) {
    setActing(actionType);
    setError(null);
    try {
      await postAction(nudge.id, actionType);
      setConfirmation(ACTION_CONFIRMATIONS[actionType]);
      confirmationTimerRef.current = setTimeout(() => onActionComplete(), 1200);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        onActionComplete();
        return;
      }
      setError(getActionErrorMessage(err));
    } finally {
      setActing(null);
    }
  }

  return (
    <section
      aria-label='Your next step'
      className='relative overflow-hidden rounded-2xl bg-[var(--color-surface)] shadow-[var(--shadow-soft)] border border-[var(--color-border)] transition-shadow duration-300 hover:shadow-lg'
    >
      {/* Decorative accent bar */}
      <div className='absolute left-0 top-0 h-1.5 w-full bg-[var(--color-primary)]'></div>

      <div className='p-6 sm:p-8'>
        <header className='mb-5 flex items-center justify-between'>
          <span className='inline-flex items-center rounded-full bg-[var(--color-accent-soft)] px-3 py-1 text-[11px] font-bold uppercase tracking-widest text-[var(--color-primary-strong)]'>
            For today
          </span>
          <span className='text-xs font-medium text-[var(--color-muted)]'>
            {formatTimestamp(nudge.created_at)}
          </span>
        </header>

        <div className='mb-6'>
          <h2 className='mb-3 font-headline text-3xl font-bold tracking-tight text-[var(--color-primary)]'>
            Your next step
          </h2>
          <p className='text-lg leading-relaxed text-[var(--color-text)]'>
            {nudge.content ?? 'We are getting this ready for you.'}
          </p>
        </div>

        {nudge.explanation && (
          <div className='rounded-xl bg-[var(--color-background)] p-5 ring-1 ring-inset ring-[var(--color-border)]/50'>
            <div className='flex items-start gap-4'>
              <svg
                className='mt-0.5 h-6 w-6 shrink-0 text-[var(--color-primary)] opacity-70'
                fill='none'
                viewBox='0 0 24 24'
                strokeWidth='1.75'
                stroke='currentColor'
                aria-hidden='true'
              >
                <path
                  strokeLinecap='round'
                  strokeLinejoin='round'
                  d='M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.82 1.508-2.316a7.5 7.5 0 10-7.516 0c.85.496 1.508 1.333 1.508 2.316V18'
                />
              </svg>
              <div>
                <h3 className='text-[11px] font-bold uppercase tracking-widest text-[var(--color-muted)] mb-1'>
                  Why this may help
                </h3>
                <p className='text-sm leading-relaxed text-[var(--color-muted)]'>
                  {nudge.explanation}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className='bg-[var(--color-surface-soft)] px-6 py-5 sm:px-8 border-t border-[var(--color-surface-strong)]'>
        {confirmation ? (
          <p
            role='status'
            className='rounded-xl bg-[var(--color-accent-soft)] px-4 py-3 text-center text-sm font-semibold text-[var(--color-accent)] animate-in fade-in duration-300'
          >
            {confirmation}
          </p>
        ) : (
          <>
            {error && (
              <p
                role='alert'
                className='mb-4 rounded-xl bg-[#fff0ee] px-4 py-3 text-sm font-medium text-[var(--color-error)]'
              >
                {error}
              </p>
            )}
            <div className='flex flex-col sm:flex-row-reverse sm:items-center sm:justify-start gap-3'>
              <button
                onClick={() => handleAction('act_now')}
                disabled={acting !== null}
                className='inline-flex items-center justify-center rounded-xl bg-[var(--color-primary)] px-6 py-2.5 text-sm font-semibold text-[var(--color-surface)] shadow-md transition-all hover:bg-[var(--color-primary-strong)] hover:shadow-lg active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60 disabled:active:scale-100'
              >
                {acting === 'act_now' ? 'Saving…' : 'I will do this'}
              </button>
              <button
                onClick={() => handleAction('ask_for_help')}
                disabled={acting !== null}
                className='inline-flex items-center justify-center rounded-xl bg-[var(--color-secondary-soft)] px-5 py-2.5 text-sm font-semibold text-[var(--color-primary)] transition-all hover:opacity-80 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60 disabled:active:scale-100'
              >
                {acting === 'ask_for_help' ? 'Saving…' : 'I need support'}
              </button>
              <button
                onClick={() => handleAction('dismiss')}
                disabled={acting !== null}
                className='inline-flex items-center justify-center rounded-xl bg-[var(--color-surface)] px-5 py-2.5 text-sm font-semibold text-[var(--color-muted)] ring-1 ring-inset ring-[var(--color-border)] transition-all hover:bg-[var(--color-surface-soft)] hover:text-[var(--color-primary)] active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60 disabled:active:scale-100'
              >
                {acting === 'dismiss' ? 'Saving…' : 'Not now'}
              </button>
            </div>
          </>
        )}
      </div>
    </section>
  );
}
