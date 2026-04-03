import { useEffect, useRef, useState } from 'react';
import type { NudgeDetail, ActionType } from '../types/member';
import { postAction, ApiError } from '../api/client';

interface Props {
  nudge: NudgeDetail;
  onActionComplete: () => void;
}

function phrasingSourceLabel(phrasingSource: string): string {
  return phrasingSource === 'llm' ? 'AI phrasing' : 'Template phrasing';
}

const ACTION_CONFIRMATIONS: Record<ActionType, string> = {
  act_now: 'Got it. We will follow up.',
  dismiss: 'Dismissed.',
  ask_for_help: 'Flagged for your coach. We will be in touch.',
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
        return 'We could not complete that action. Please try again.';
      }

      if (err.status === 422) {
        return 'That action could not be recorded. Please try again.';
      }

      if (err.status === 0 || err.status >= 500) {
        return 'We could not complete that action. Please try again.';
      }
    }

    return 'We could not complete that action. Please try again.';
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
      aria-label='Personalized nudge'
      className='bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden'
    >
      <div className='p-6'>
        <div className='flex items-center justify-between gap-3 mb-3'>
          <h2 className='text-lg font-semibold text-gray-900'>
            Your recommendation
          </h2>
          <span className='inline-flex items-center rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600'>
            {phrasingSourceLabel(nudge.phrasing_source)}
          </span>
        </div>
        <p className='text-gray-800 leading-relaxed'>{nudge.content}</p>
      </div>

      {nudge.explanation && (
        <details className='border-t border-gray-100 px-6 py-4 group'>
          <summary className='text-sm font-medium text-gray-500 cursor-pointer select-none hover:text-gray-700'>
            Why am I seeing this?
          </summary>
          <p className='mt-2 text-sm text-gray-600 leading-relaxed'>
            {nudge.explanation}
          </p>
        </details>
      )}

      <div className='border-t border-gray-100 px-6 py-4'>
        {confirmation ? (
          <p
            role='status'
            className='text-sm font-medium text-green-700 bg-green-50 rounded-lg px-4 py-3 text-center'
          >
            {confirmation}
          </p>
        ) : (
          <>
            {error && (
              <p role='alert' className='text-sm text-red-600 mb-3'>
                {error}
              </p>
            )}
            <div className='flex flex-wrap gap-3'>
              <button
                onClick={() => handleAction('act_now')}
                disabled={acting !== null}
                className='px-5 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors'
              >
                {acting === 'act_now' ? 'Saving…' : 'Act now'}
              </button>
              <button
                onClick={() => handleAction('dismiss')}
                disabled={acting !== null}
                className='px-5 py-2.5 bg-white text-gray-700 text-sm font-medium rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50 transition-colors'
              >
                {acting === 'dismiss' ? 'Saving…' : 'Dismiss'}
              </button>
              <button
                onClick={() => handleAction('ask_for_help')}
                disabled={acting !== null}
                className='px-5 py-2.5 text-gray-500 text-sm underline hover:text-gray-700 disabled:opacity-50 transition-colors'
              >
                {acting === 'ask_for_help' ? 'Saving…' : 'Ask for help'}
              </button>
            </div>
          </>
        )}
      </div>
    </section>
  );
}
