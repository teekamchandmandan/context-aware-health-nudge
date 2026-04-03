import { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { fetchNudge, ApiError } from '../api/client';
import type { MemberNudgeResponse, NudgeState } from '../types/member';
import { SEEDED_MEMBERS } from '../types/member';
import MemberSwitcher from '../components/MemberSwitcher';
import NudgeCard from '../components/NudgeCard';
import QuickLog from '../components/QuickLog';
import Spinner from '../components/Spinner';
import SectionError from '../components/SectionError';

export default function MemberPage() {
  const [searchParams, setSearchParams] = useSearchParams();
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

      setError('We could not load your nudge. Please try again.');
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

  function refetchNudge() {
    loadNudge(memberId);
  }

  function handleResetComplete(nextMemberId: string) {
    setSearchParams({ memberId: nextMemberId });
    loadNudge(nextMemberId);
  }

  const state: NudgeState = data?.state ?? 'active';

  return (
    <div className='min-h-screen bg-gray-50'>
      <div className='max-w-2xl mx-auto px-4 py-8 space-y-6'>
        {/* Header */}
        <header>
          <div className='flex items-center justify-between mb-4'>
            <h1 className='text-xl font-bold text-gray-900'>Digbi Health</h1>
            <Link
              to='/coach'
              className='text-sm text-blue-600 hover:text-blue-800 font-medium transition-colors'
            >
              Coach dashboard →
            </Link>
          </div>
          <MemberSwitcher
            onMemberChange={handleMemberChange}
            onResetComplete={handleResetComplete}
          />
        </header>

        {/* Signal logging */}
        <QuickLog
          key={memberId}
          memberId={memberId}
          onSignalSubmitted={refetchNudge}
        />

        {/* Nudge area */}
        <div aria-live='polite' className='visible'>
          {loading && <Spinner />}

          {!loading && error && (
            <SectionError message={error} onRetry={refetchNudge} />
          )}

          {!loading && !error && state === 'active' && data?.nudge && (
            <NudgeCard nudge={data.nudge} onActionComplete={refetchNudge} />
          )}

          {!loading && !error && state === 'no_nudge' && (
            <div className='bg-white rounded-xl border border-gray-200 p-6 text-center'>
              <p className='text-gray-600'>
                No action needed right now. Check back later after you log your
                next update.
              </p>
            </div>
          )}

          {!loading && !error && state === 'escalated' && (
            <div className='bg-amber-50 rounded-xl border border-amber-200 p-6 text-center'>
              <p className='text-amber-800'>
                We have flagged this for coach review instead of showing an
                automated suggestion.
              </p>
            </div>
          )}
        </div>

        {/* Member info footer */}
        {data?.member && !loading && (
          <p className='text-xs text-gray-400 text-center'>
            Viewing as {data.member.name} ({data.member.id})
          </p>
        )}
      </div>
    </div>
  );
}
