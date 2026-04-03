import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  fetchCoachNudges,
  fetchCoachEscalations,
  ApiError,
} from '../api/client';
import type { CoachNudgeItem, CoachEscalationItem } from '../types/member';
import CoachNudgesList from '../components/CoachNudgesList';
import CoachEscalationsList from '../components/CoachEscalationsList';

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

  return (
    <div className='min-h-screen bg-gray-50'>
      <div className='max-w-6xl mx-auto px-4 py-8 space-y-6'>
        {/* Header */}
        <header className='flex items-center justify-between'>
          <h1 className='text-xl font-bold text-gray-900'>Coach Dashboard</h1>
          <Link
            to='/member'
            className='text-sm text-blue-600 hover:text-blue-800 font-medium transition-colors'
          >
            ← Member view
          </Link>
        </header>

        {/* Two-column layout on large screens, stacked on small */}
        <div className='grid grid-cols-1 lg:grid-cols-[1fr_2fr] gap-6'>
          {/* Left: Escalations */}
          <section>
            <h2 className='text-base font-semibold text-gray-900 mb-3'>
              Open Escalations
              {!escalationsLoading && !escalationsError && (
                <span className='ml-2 text-sm font-normal text-gray-400'>
                  ({escalations.length})
                </span>
              )}
            </h2>

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

          {/* Right: Recent nudges */}
          <section>
            <h2 className='text-base font-semibold text-gray-900 mb-3'>
              Recent Nudges
              {!nudgesLoading && !nudgesError && (
                <span className='ml-2 text-sm font-normal text-gray-400'>
                  ({nudges.length})
                </span>
              )}
            </h2>

            {nudgesLoading && <Spinner />}

            {!nudgesLoading && nudgesError && (
              <SectionError message={nudgesError} onRetry={loadNudges} />
            )}

            {!nudgesLoading && !nudgesError && (
              <CoachNudgesList items={nudges} />
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

function Spinner() {
  return (
    <div className='flex justify-center py-12'>
      <div
        className='h-6 w-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin'
        role='status'
      >
        <span className='sr-only'>Loading…</span>
      </div>
    </div>
  );
}

function SectionError({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div className='bg-white rounded-xl border border-red-200 p-6 text-center'>
      <p className='text-gray-700 mb-3'>{message}</p>
      <button
        onClick={onRetry}
        className='px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors'
      >
        Try again
      </button>
    </div>
  );
}
