import { useCallback, useEffect, useRef, useState } from 'react';
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

const STATE_COPY: Record<NudgeState, { description: string }> = {
  active: {
    description: 'We have a suggestion based on your recent activity.',
  },
  no_nudge: {
    description:
      'Nothing needs your attention right now. We will let you know when something comes up.',
  },
  escalated: {
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
  const abortRef = useRef<AbortController | null>(null);

  const loadNudge = useCallback(async (id: string) => {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setLoading(true);
    setError(null);
    try {
      const res = await fetchNudge(id, ac.signal);
      if (!ac.signal.aborted) setData(res);
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') return;
      if (err instanceof ApiError && err.status === 404) {
        console.error('Member nudge endpoint returned 404', err.body);
      }

      setError('We could not load this right now. Please try again.');
    } finally {
      if (!ac.signal.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadNudge(memberId);
    return () => abortRef.current?.abort();
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
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    try {
      const res = await fetchNudge(memberId, ac.signal);
      if (!ac.signal.aborted) setData(res);
    } catch {
      /* swallow — nudge section keeps its previous state */
    }
  }, [memberId]);

  const state: NudgeState | null = data?.state ?? null;
  const currentMember =
    SEEDED_MEMBERS.find((member) => member.id === memberId) ??
    SEEDED_MEMBERS[0];
  const memberName = data?.member.name ?? currentMember.name;
  const stateCopy = state ? STATE_COPY[state] : null;
  const lastUpdatedLabel = data?.nudge?.created_at
    ? formatTimestamp(data.nudge.created_at)
    : loading
      ? 'Loading…'
      : null;

  function renderNudgeSection() {
    if (loading) {
      return <Spinner />;
    }

    if (error) {
      return <SectionError message={error} onRetry={refetchNudge} />;
    }

    if (state === 'active' && data?.nudge) {
      return <NudgeCard nudge={data.nudge} onActionComplete={refetchNudge} />;
    }

    if (state === 'no_nudge') {
      return (
        <div className='rounded-[1.75rem] border border-white/80 bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(242,244,244,0.95))] p-8 text-left shadow-[0_16px_48px_rgba(25,28,29,0.05)]'>
          <p className='text-sm font-semibold uppercase tracking-[0.18em] text-[var(--color-muted)]'>
            All set
          </p>
          <h2 className='mt-3 font-headline text-2xl font-bold tracking-[-0.04em] text-[var(--color-primary)]'>
            Your routine looks steady today.
          </h2>
          <p className='mt-4 max-w-2xl text-base leading-8 text-[var(--color-muted)]'>
            Nothing needs your attention right now. Check in again whenever you
            are ready.
          </p>
        </div>
      );
    }

    if (state === 'escalated') {
      return (
        <div className='rounded-[1.75rem] border border-[#f2dba8] bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(255,241,214,0.9))] p-8 text-left shadow-[0_16px_48px_rgba(25,28,29,0.05)]'>
          <p className='text-sm font-semibold uppercase tracking-[0.18em] text-[var(--color-warning-text)]'>
            Support update
          </p>
          <h2 className='mt-3 font-headline text-2xl font-bold tracking-[-0.04em] text-[#5e4700]'>
            Someone from your care team will take a look.
          </h2>
          <p className='mt-4 max-w-2xl text-base leading-8 text-[var(--color-warning-text)]'>
            You can keep using this page while someone reviews your update.
          </p>
        </div>
      );
    }

    return null;
  }

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
            {stateCopy?.description ?? '\u00A0'}
          </p>
          {lastUpdatedLabel && (
            <p className='mt-4 text-sm text-[var(--color-muted)]'>
              Last updated {lastUpdatedLabel}
            </p>
          )}
        </section>

        <section className='mb-8'>
          <div className='visible' aria-live='polite'>
            {renderNudgeSection()}
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
