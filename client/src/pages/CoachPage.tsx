import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  fetchCoachNudges,
  fetchCoachEscalations,
  resolveEscalation,
  ApiError,
} from '../api/client';
import type { CoachNudgeItem, CoachEscalationItem } from '../types/member';
import CoachNudgesList from '../components/CoachNudgesList';
import CoachEscalationsList from '../components/CoachEscalationsList';
import Spinner from '../components/Spinner';
import SectionError from '../components/SectionError';

function getEscalationSummary(
  escalationsLoading: boolean,
  openCount: number,
): string {
  if (escalationsLoading) {
    return 'Checking for open escalations…';
  }

  if (openCount === 0) {
    return 'All members are on track. No open escalations right now.';
  }

  const noun = openCount === 1 ? 'escalation' : 'escalations';
  const verb = openCount === 1 ? 'needs' : 'need';

  return `You have ${openCount} open ${noun} that ${verb} attention.`;
}

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

  async function handleResolve(escalationId: string) {
    await resolveEscalation(escalationId);
    await loadEscalations();
  }

  const openCount = escalations.length;
  const coachSummary = getEscalationSummary(escalationsLoading, openCount);

  return (
    <div className='min-h-screen text-[var(--color-text)]'>
      <a
        href='#coach-main'
        className='sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-[var(--color-primary)] focus:px-4 focus:py-3 focus:text-sm focus:font-semibold focus:text-white'
      >
        Skip to main content
      </a>

      <header className='relative z-20 mb-10 bg-[linear-gradient(180deg,rgba(255,255,255,0.28),rgba(255,255,255,0.08))] backdrop-blur-sm'>
        <div className='mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8'>
          <p className='font-headline text-3xl font-extrabold leading-none tracking-[-0.05em] text-[var(--color-primary)] sm:text-[2.6rem]'>
            Health Nudge
          </p>
          <div className='flex items-center gap-3'>
            <Link
              to='/member'
              className='rounded-full border border-white/70 bg-white/60 px-4 py-2 text-sm font-medium text-[var(--color-muted)] transition hover:border-[var(--color-primary)] hover:bg-white hover:text-[var(--color-primary)]'
            >
              Member view
            </Link>
            <button
              type='button'
              onClick={refreshAll}
              className='inline-flex items-center gap-2 rounded-full border border-white/70 bg-white/85 px-4 py-2 text-sm font-semibold text-[var(--color-primary)] shadow-[0_10px_30px_rgba(25,28,29,0.08)] transition hover:border-[var(--color-primary)] hover:bg-white'
            >
              <svg
                className='h-4 w-4'
                fill='none'
                viewBox='0 0 24 24'
                strokeWidth={2}
                stroke='currentColor'
              >
                <path
                  strokeLinecap='round'
                  strokeLinejoin='round'
                  d='M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.992 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182'
                />
              </svg>
              Refresh
            </button>
          </div>
        </div>
      </header>

      <main
        id='coach-main'
        className='mx-auto max-w-5xl px-4 pb-12 pt-6 sm:px-6 lg:px-8 lg:pb-16'
      >
        <section className='mb-10'>
          <p className='text-sm font-semibold uppercase tracking-[0.18em] text-[var(--color-muted)]'>
            Coach dashboard
          </p>
          <h1 className='mt-2 font-headline text-balance text-3xl font-extrabold tracking-[-0.04em] text-[var(--color-primary)] sm:text-4xl'>
            Good to see you, Coach
          </h1>
          <p className='mt-3 max-w-2xl text-base leading-8 text-[var(--color-muted)] sm:text-lg'>
            {coachSummary}
          </p>
        </section>

        <section className='mb-12'>
          <div className='mb-4 flex items-center gap-3'>
            <h2 className='font-headline text-xl font-bold tracking-[-0.04em] text-[var(--color-primary)]'>
              Escalations
            </h2>
            {!escalationsLoading && !escalationsError && openCount > 0 && (
              <span className='inline-flex h-6 min-w-6 items-center justify-center rounded-full bg-[rgba(255,209,102,0.35)] px-2 text-xs font-bold text-[var(--color-warning-text)]'>
                {openCount}
              </span>
            )}
          </div>

          <div className='visible' aria-live='polite'>
            {escalationsLoading && <Spinner />}

            {!escalationsLoading && escalationsError && (
              <SectionError
                message={escalationsError}
                onRetry={loadEscalations}
              />
            )}

            {!escalationsLoading && !escalationsError && (
              <CoachEscalationsList
                items={escalations}
                onResolve={handleResolve}
              />
            )}
          </div>
        </section>

        <section>
          <div className='mb-4 flex items-center gap-3'>
            <h2 className='font-headline text-xl font-bold tracking-[-0.04em] text-[var(--color-primary)]'>
              Recent nudges
            </h2>
            {!nudgesLoading && !nudgesError && (
              <span className='inline-flex h-6 min-w-6 items-center justify-center rounded-full bg-[rgba(168,239,239,0.36)] px-2 text-xs font-bold text-[var(--color-primary)]'>
                {nudges.length}
              </span>
            )}
          </div>

          <div className='visible' aria-live='polite'>
            {nudgesLoading && <Spinner />}

            {!nudgesLoading && nudgesError && (
              <SectionError message={nudgesError} onRetry={loadNudges} />
            )}

            {!nudgesLoading && !nudgesError && (
              <CoachNudgesList items={nudges} />
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
