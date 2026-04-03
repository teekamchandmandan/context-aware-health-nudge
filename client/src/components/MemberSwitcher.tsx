import { useSearchParams } from 'react-router-dom';
import { SEEDED_MEMBERS } from '../types/member';
import { ApiError, resetSeed } from '../api/client';
import { useState } from 'react';

interface Props {
  onMemberChange: () => void;
  onResetComplete: (memberId: string) => void;
}

export default function MemberSwitcher({
  onMemberChange,
  onResetComplete,
}: Props) {
  const [searchParams, setSearchParams] = useSearchParams();
  const currentId = searchParams.get('memberId') ?? SEEDED_MEMBERS[0].id;
  const [resetting, setResetting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function selectMember(id: string) {
    setSearchParams({ memberId: id });
    setError(null);
    onMemberChange();
  }

  async function handleReset() {
    setResetting(true);
    setError(null);
    try {
      await resetSeed();
      onResetComplete(currentId);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        console.error('Reset endpoint not found', err.body);
      }
      setError('We could not reset the demo data. Please try again.');
    } finally {
      setResetting(false);
    }
  }

  return (
    <nav aria-label='Demo member selector' className='space-y-2'>
      <div className='flex flex-wrap items-center gap-3'>
        <div
          className='flex rounded-lg border border-gray-200 overflow-hidden'
          role='group'
        >
          {SEEDED_MEMBERS.map((m) => (
            <button
              key={m.id}
              onClick={() => selectMember(m.id)}
              aria-pressed={currentId === m.id}
              className={`px-4 py-2 text-sm font-medium transition-colors border-r last:border-r-0 border-gray-200
                ${
                  currentId === m.id
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-50'
                }`}
            >
              <span className='block'>{m.name}</span>
              <span className='block text-xs opacity-75'>{m.scenario}</span>
            </button>
          ))}
        </div>
        <button
          onClick={handleReset}
          disabled={resetting}
          className='ml-auto text-xs text-gray-400 hover:text-gray-600 underline disabled:opacity-50'
        >
          {resetting ? 'Resetting…' : 'Reset demo data'}
        </button>
      </div>
      {error && (
        <p role='alert' className='text-sm text-red-600'>
          {error}
        </p>
      )}
    </nav>
  );
}
