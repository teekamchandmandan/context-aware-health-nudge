import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { fetchNudge, ApiError } from '../api/client';
import type { MemberNudgeResponse, NudgeState } from '../types/member';
import { SEEDED_MEMBERS } from '../types/member';
import MemberSwitcher from '../components/MemberSwitcher';
import NudgeCard from '../components/NudgeCard';
import QuickLog from '../components/QuickLog';
import Spinner from '../components/Spinner';
import SectionError from '../components/SectionError';
import { formatTimestamp } from '../utils/formatTimestamp';

const STATE_COPY: Record<
  NudgeState,
  { greeting: string; description: string }
> = {
  active: {
    greeting: 'Here is what to focus on next.',
    description: 'We have a suggestion based on your recent activity.',
  },
  no_nudge: {
    greeting: 'You are all caught up.',
    description:
      'Nothing needs your attention right now. We will let you know when something comes up.',
  },
  escalated: {
    greeting: 'Your care team is on it.',
    description:
      'Someone will follow up soon. You can still log updates below.',
  },
};

export default function MemberPage() {
  const [searchParams] = useSearchParams();
  const memberId = searchParams.get('memberId') ?? SEEDED_MEMBERS[0].id;

  const [data, setData] = useState<MemberNudgeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadNudge = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchNudge(id);
      setData(res);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        console.error('Member nudge endpoint returned 404', err.body);
      }

      setError('We could not load this right now. Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadNudge(memberId);
  }, [memberId, loadNudge]);

  function handleMemberChange() {
    setData(null);
    setLoading(true);
    setError(null);
  }

  const refetchNudge = useCallback(() => {
    loadNudge(memberId);
  }, [memberId, loadNudge]);

  /* Silent refresh: update data without flashing the loading spinner. */
  const silentRefetch = useCallback(async () => {
    try {
      const res = await fetchNudge(memberId);
      setData(res);
    } catch {
      /* swallow — nudge section keeps its previous state */
    }
  }, [memberId]);

  const state: NudgeState = data?.state ?? 'active';
  const currentMember =
    SEEDED_MEMBERS.find((member) => member.id === memberId) ??
    SEEDED_MEMBERS[0];
  const memberName = data?.member.name ?? currentMember.name;
  const stateCopy = STATE_COPY[state];
  const lastUpdatedLabel = data?.nudge?.created_at
    ? formatTimestamp(data.nudge.created_at)
    : loading
      ? 'Loading…'
      : null;

  return (
    <div className='min-h-screen text-[var(--color-text)]'>
      <a
        href='#member-main'
        className='sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-[var(--color-primary)] focus:px-4 focus:py-3 focus:text-sm focus:font-semibold focus:text-white'
      >
        Skip to main content
      </a>

      <header className='relative z-20 mb-10 bg-[linear-gradient(180deg,rgba(255,255,255,0.28),rgba(255,255,255,0.08))] backdrop-blur-sm'>
        <div className='mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8'>
          <div>
            <p className='font-headline text-3xl font-extrabold leading-none tracking-[-0.05em] text-[var(--color-primary)] sm:text-[2.6rem]'>
              Health Nudge
            </p>
          </div>
          <MemberSwitcher
            currentMemberName={memberName}
            onMemberChange={handleMemberChange}
          />
        </div>
      </header>

      <main
        id='member-main'
        className='mx-auto max-w-5xl px-4 pb-12 pt-6 sm:px-6 lg:px-8 lg:pb-16'
      >
        <section className='mb-8'>
          <h1 className='font-headline text-balance text-3xl font-extrabold tracking-[-0.04em] text-[var(--color-primary)] sm:text-4xl'>
            Hi {memberName}
          </h1>
          <p className='mt-3 max-w-2xl text-base leading-8 text-[var(--color-muted)] sm:text-lg'>
            {stateCopy.description}
          </p>
          {lastUpdatedLabel && (
            <p className='mt-4 text-sm text-[var(--color-muted)]'>
              Last updated {lastUpdatedLabel}
            </p>
          )}
        </section>

        <section className='mb-8'>
          <div className='visible' aria-live='polite'>
            {loading && <Spinner />}

            {!loading && error && (
              <SectionError message={error} onRetry={refetchNudge} />
            )}

            {!loading && !error && state === 'active' && data?.nudge && (
              <NudgeCard nudge={data.nudge} onActionComplete={refetchNudge} />
            )}

            {!loading && !error && state === 'no_nudge' && (
              <div className='rounded-[1.75rem] border border-white/80 bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(242,244,244,0.95))] p-8 text-left shadow-[0_16px_48px_rgba(25,28,29,0.05)]'>
                <p className='text-sm font-semibold uppercase tracking-[0.18em] text-[var(--color-muted)]'>
                  All set
                </p>
                <h2 className='mt-3 font-headline text-2xl font-bold tracking-[-0.04em] text-[var(--color-primary)]'>
                  Your routine looks steady today.
                </h2>
                <p className='mt-4 max-w-2xl text-base leading-8 text-[var(--color-muted)]'>
                  Nothing needs your attention right now. Check in again
                  whenever you are ready.
                </p>
              </div>
            )}

            {!loading && !error && state === 'escalated' && (
              <div className='rounded-[1.75rem] border border-[#f2dba8] bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(255,241,214,0.9))] p-8 text-left shadow-[0_16px_48px_rgba(25,28,29,0.05)]'>
                <p className='text-sm font-semibold uppercase tracking-[0.18em] text-[var(--color-warning-text)]'>
                  Support update
                </p>
                <h2 className='mt-3 font-headline text-2xl font-bold tracking-[-0.04em] text-[#5e4700]'>
                  Someone from your care team will take a look.
                </h2>
                <p className='mt-4 max-w-2xl text-base leading-8 text-[var(--color-warning-text)]'>
                  You can keep using this page while someone reviews your
                  update.
                </p>
              </div>
            )}
          </div>
        </section>

        <section>
          <h2 className='mb-1 font-headline text-xl font-bold tracking-[-0.04em] text-[var(--color-primary)]'>
            Quick check-ins
          </h2>
          <p className='mb-4 text-sm text-[var(--color-muted)]'>
            Log a few things to keep your guidance accurate.
          </p>
          <QuickLog
            key={memberId}
            memberId={memberId}
            onSignalSubmitted={silentRefetch}
          />
        </section>
      </main>
    </div>
  );
}
