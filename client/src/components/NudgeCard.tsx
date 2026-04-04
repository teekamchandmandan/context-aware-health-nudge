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
    if (err instanceof ApiError) {
      if (err.status === 404) {
        console.error('Nudge action endpoint returned 404', err.body);
        return 'We could not save that. Please try again.';
      }

      if (err.status === 422) {
        return 'We could not save that. Please try again.';
      }

      if (err.status === 0 || err.status >= 500) {
        return 'We could not save that. Please try again.';
      }
    }

    return 'We could not save that. Please try again.';
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
      className='overflow-hidden rounded-[2rem] border border-white/80 bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(242,244,244,0.94))] shadow-[0_20px_60px_rgba(25,28,29,0.06)]'
    >
      <div className='border-b border-[rgba(190,200,200,0.45)] bg-[linear-gradient(135deg,rgba(168,239,239,0.28),rgba(255,255,255,0.92))] p-6 sm:p-8'>
        <div className='mb-5 flex flex-wrap items-center gap-3'>
          <span className='rounded-full bg-white/80 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-[var(--color-muted)]'>
            For today
          </span>
        </div>

        <h2 className='font-headline text-3xl font-extrabold tracking-[-0.04em] text-[var(--color-primary)] sm:text-4xl'>
          Your next step
        </h2>
        <p className='mt-4 max-w-3xl text-lg leading-8 text-[var(--color-text)]'>
          {nudge.content ?? 'We are getting this ready for you.'}
        </p>
        <p className='mt-5 text-sm font-medium text-[var(--color-muted)]'>
          Updated {formatTimestamp(nudge.created_at)}
        </p>
      </div>

      {nudge.explanation && (
        <div className='border-b border-[rgba(190,200,200,0.45)] px-6 py-6 sm:px-8'>
          <p className='text-sm font-semibold uppercase tracking-[0.18em] text-[var(--color-muted)]'>
            Why this may help
          </p>
          <p className='mt-3 text-base leading-8 text-[var(--color-muted)]'>
            {nudge.explanation}
          </p>
        </div>
      )}

      <div className='px-6 py-6 sm:px-8'>
        {confirmation ? (
          <p
            role='status'
            className='rounded-[1.25rem] bg-[rgba(143,246,208,0.22)] px-5 py-4 text-center text-sm font-semibold text-[var(--color-accent)]'
          >
            {confirmation}
          </p>
        ) : (
          <>
            {error && (
              <p
                role='alert'
                className='mb-4 rounded-[1rem] bg-[#fff0ee] px-4 py-3 text-sm font-medium text-[var(--color-error)]'
              >
                {error}
              </p>
            )}
            <div className='flex flex-col gap-3 sm:flex-row sm:flex-wrap'>
              <button
                onClick={() => handleAction('act_now')}
                disabled={acting !== null}
                className='inline-flex items-center justify-center rounded-[1rem] bg-[var(--color-primary)] px-5 py-3 text-sm font-semibold text-white shadow-[0_16px_36px_rgba(0,66,66,0.18)] transition hover:-translate-y-0.5 hover:bg-[var(--color-primary-strong)] disabled:cursor-not-allowed disabled:opacity-60'
              >
                {acting === 'act_now' ? 'Saving…' : 'I will do this'}
              </button>
              <button
                onClick={() => handleAction('ask_for_help')}
                disabled={acting !== null}
                className='inline-flex items-center justify-center rounded-[1rem] bg-[rgba(186,235,245,0.66)] px-5 py-3 text-sm font-semibold text-[var(--color-primary)] transition hover:-translate-y-0.5 hover:bg-[rgba(186,235,245,0.9)] disabled:cursor-not-allowed disabled:opacity-60'
              >
                {acting === 'ask_for_help' ? 'Saving…' : 'I need support'}
              </button>
              <button
                onClick={() => handleAction('dismiss')}
                disabled={acting !== null}
                className='inline-flex items-center justify-center rounded-[1rem] border border-[rgba(190,200,200,0.9)] bg-white px-5 py-3 text-sm font-semibold text-[var(--color-muted)] transition hover:-translate-y-0.5 hover:border-[var(--color-primary)] hover:text-[var(--color-primary)] disabled:cursor-not-allowed disabled:opacity-60'
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
