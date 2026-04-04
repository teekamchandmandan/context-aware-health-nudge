import { useCallback, useEffect, useState } from 'react';
import {
  fetchCoachNudges,
  fetchCoachEscalations,
  ApiError,
} from '../api/client';
import type { CoachNudgeItem, CoachEscalationItem } from '../types/member';
import CoachNudgesList from '../components/CoachNudgesList';
import CoachEscalationsList from '../components/CoachEscalationsList';
import Spinner from '../components/Spinner';
import SectionError from '../components/SectionError';

export default function CoachPage() {
  const [nudges, setNudges] = useState<CoachNudgeItem[]>([]);
  const [escalations, setEscalations] = useState<CoachEscalationItem[]>([]);
  const [nudgesLoading, setNudgesLoading] = useState(true);
  const [escalationsLoading, setEscalationsLoading] = useState(true);
  const [nudgesError, setNudgesError] = useState<string | null>(null);
  const [escalationsError, setEscalationsError] = useState<string | null>(null);

  const loadNudges = useCallback(async () => {
    setNudgesLoading(true);
    setNudgesError(null);
    try {
      const res = await fetchCoachNudges();
      setNudges(res.items);
    } catch (err) {
      if (err instanceof ApiError) {
        console.error('Coach nudges fetch failed', err.status, err.body);
      }
      setNudgesError('Could not load recent nudges.');
    } finally {
      setNudgesLoading(false);
    }
  }, []);

  const loadEscalations = useCallback(async () => {
    setEscalationsLoading(true);
    setEscalationsError(null);
    try {
      const res = await fetchCoachEscalations();
      setEscalations(res.items);
    } catch (err) {
      if (err instanceof ApiError) {
        console.error('Coach escalations fetch failed', err.status, err.body);
      }
      setEscalationsError('Could not load escalations.');
    } finally {
      setEscalationsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadNudges();
    loadEscalations();
  }, [loadNudges, loadEscalations]);

  function refreshAll() {
    loadNudges();
    loadEscalations();
  }

  const openCount = escalations.length;

  return (
    <div className='min-h-screen text-[var(--color-text)]'>
      <header className='relative z-20 mb-10 bg-[linear-gradient(180deg,rgba(255,255,255,0.28),rgba(255,255,255,0.08))] backdrop-blur-sm'>
        <div className='mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8'>
          <p className='font-headline text-3xl font-extrabold leading-none tracking-[-0.05em] text-[var(--color-primary)] sm:text-[2.6rem]'>
            Health Nudge
          </p>
          <button
            type='button'
            onClick={refreshAll}
            className='rounded-full border border-white/70 bg-white/85 px-4 py-2 text-sm font-semibold text-[var(--color-primary)] shadow-[0_10px_30px_rgba(25,28,29,0.08)] transition hover:border-[var(--color-primary)] hover:bg-white'
          >
            Refresh
          </button>
        </div>
      </header>

      <main className='mx-auto max-w-5xl px-4 pb-12 pt-6 sm:px-6 lg:px-8 lg:pb-16'>
        <section className='mb-8'>
          <h1 className='font-headline text-3xl font-extrabold tracking-[-0.04em] text-[var(--color-primary)] sm:text-4xl'>
            Good to see you, Coach
          </h1>
          <p className='mt-2 text-base text-[var(--color-muted)]'>
            {escalationsLoading
              ? 'Checking for open escalations…'
              : openCount === 0
                ? 'No open escalations right now.'
                : `${openCount} open escalation${openCount === 1 ? '' : 's'}`}
          </p>
        </section>

        <section className='mb-10'>
          {escalationsLoading && <Spinner />}

          {!escalationsLoading && escalationsError && (
            <SectionError
              message={escalationsError}
              onRetry={loadEscalations}
            />
          )}

          {!escalationsLoading && !escalationsError && (
            <CoachEscalationsList items={escalations} />
          )}
        </section>

        <section>
          <h2 className='mb-4 font-headline text-xl font-bold tracking-[-0.04em] text-[var(--color-primary)]'>
            Recent nudges
            {!nudgesLoading && !nudgesError && (
              <span className='ml-2 text-base font-normal text-[var(--color-muted)]'>
                ({nudges.length})
              </span>
            )}
          </h2>

          {nudgesLoading && <Spinner />}

          {!nudgesLoading && nudgesError && (
            <SectionError message={nudgesError} onRetry={loadNudges} />
          )}

          {!nudgesLoading && !nudgesError && <CoachNudgesList items={nudges} />}
        </section>
      </main>
    </div>
  );
}
