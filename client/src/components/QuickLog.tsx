import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchLatestSignals } from '../api/client';
import type { LatestSignalsResponse } from '../types/member';
import { formatTimestamp } from '../utils/formatTimestamp';
import LogCard from './quick-log/LogCard';
import MealForm from './quick-log/MealForm';
import MoodForm from './quick-log/MoodForm';
import SleepForm from './quick-log/SleepForm';
import WeightForm from './quick-log/WeightForm';
import { MOOD_LABELS } from './quick-log/shared';
import { useCardFeedback } from './quick-log/useCardFeedback';
import ToastContainer from './Toast';
import { createToastId, type ToastItem } from './Toast.shared';

interface Props {
  memberId: string;
  onSignalSubmitted: () => void;
}

export default function QuickLog({ memberId, onSignalSubmitted }: Props) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [latest, setLatest] = useState<LatestSignalsResponse>({});
  const refreshControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const ac = new AbortController();
    fetchLatestSignals(memberId, ac.signal)
      .then(setLatest)
      .catch(() => {});
    return () => ac.abort();
  }, [memberId]);

  const showToast = useCallback(
    (message: string) => {
      setToasts((prev) => [...prev, { id: createToastId(), message }]);
      onSignalSubmitted();
      // Cancel any in-flight refresh, then start a new one
      refreshControllerRef.current?.abort();
      const ac = new AbortController();
      refreshControllerRef.current = ac;
      fetchLatestSignals(memberId, ac.signal)
        .then(setLatest)
        .catch(() => {});
    },
    [memberId, onSignalSubmitted],
  );

  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const weight = useCardFeedback(showToast);
  const mood = useCardFeedback(showToast);
  const meal = useCardFeedback(showToast);
  const sleep = useCardFeedback(showToast);

  const getFormProps = (feedback: typeof weight) => ({
    memberId,
    submitting: feedback.submitting,
    setSubmitting: feedback.setSubmitting,
    onSuccess: feedback.handleSuccess,
    onError: feedback.setApiError,
    clearFeedback: feedback.clearFeedback,
  });

  const lastWeight = latest.weight_logged;
  const lastSleep = latest.sleep_logged;
  const lastMood = latest.mood_logged;

  function lastLoggedText(value: string, loggedAt?: string) {
    return loggedAt
      ? `Last: ${value} · ${formatTimestamp(loggedAt)}`
      : undefined;
  }

  return (
    <>
      <div className='grid gap-4 grid-cols-1 sm:grid-cols-3'>
        <LogCard
          eyebrow='Weight'
          title='Track your weight'
          subtitle={lastLoggedText(
            lastWeight?.payload?.weight_lb != null
              ? `${lastWeight.payload.weight_lb} lb`
              : '',
            lastWeight?.logged_at,
          )}
          apiError={weight.apiError}
        >
          <WeightForm {...getFormProps(weight)} />
        </LogCard>

        <LogCard
          eyebrow='Sleep'
          title='How many hours?'
          subtitle={lastLoggedText(
            lastSleep?.payload?.sleep_hours != null
              ? `${lastSleep.payload.sleep_hours}h`
              : '',
            lastSleep?.logged_at,
          )}
          apiError={sleep.apiError}
        >
          <SleepForm {...getFormProps(sleep)} />
        </LogCard>

        <LogCard
          eyebrow='Mood'
          title='How are you feeling?'
          subtitle={lastLoggedText(
            lastMood?.payload?.mood
              ? (
                  MOOD_LABELS[lastMood.payload.mood] ?? lastMood.payload.mood
                ).toLowerCase()
              : '',
            lastMood?.logged_at,
          )}
          apiError={mood.apiError}
        >
          <MoodForm {...getFormProps(mood)} />
        </LogCard>

        <LogCard
          eyebrow='Meal log'
          title='What did you eat?'
          apiError={meal.apiError}
          className='sm:col-span-3'
        >
          <MealForm {...getFormProps(meal)} />
        </LogCard>
      </div>
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </>
  );
}
