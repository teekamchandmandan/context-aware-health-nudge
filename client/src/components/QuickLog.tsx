import { useCallback, useState } from 'react';
import LogCard from './quick-log/LogCard';
import MealForm from './quick-log/MealForm';
import MoodForm from './quick-log/MoodForm';
import SleepForm from './quick-log/SleepForm';
import WeightForm from './quick-log/WeightForm';
import { useCardFeedback } from './quick-log/useCardFeedback';
import ToastContainer, { createToastId, type ToastItem } from './Toast';

interface Props {
  memberId: string;
  onSignalSubmitted: () => void;
}

export default function QuickLog({ memberId, onSignalSubmitted }: Props) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const showToast = useCallback(
    (message: string) => {
      setToasts((prev) => [...prev, { id: createToastId(), message }]);
      onSignalSubmitted();
    },
    [onSignalSubmitted],
  );

  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const weight = useCardFeedback(showToast);
  const mood = useCardFeedback(showToast);
  const meal = useCardFeedback(showToast);
  const sleep = useCardFeedback(showToast);

  return (
    <>
      <div className='grid gap-4 grid-cols-1 sm:grid-cols-3'>
        <LogCard
          eyebrow='Weight'
          title='Track your weight'
          apiError={weight.apiError}
        >
          <WeightForm
            memberId={memberId}
            submitting={weight.submitting}
            setSubmitting={weight.setSubmitting}
            onSuccess={weight.handleSuccess}
            onError={weight.setApiError}
            clearFeedback={weight.clearFeedback}
          />
        </LogCard>

        <LogCard
          eyebrow='Sleep'
          title='How many hours?'
          apiError={sleep.apiError}
        >
          <SleepForm
            memberId={memberId}
            submitting={sleep.submitting}
            setSubmitting={sleep.setSubmitting}
            onSuccess={sleep.handleSuccess}
            onError={sleep.setApiError}
            clearFeedback={sleep.clearFeedback}
          />
        </LogCard>

        <LogCard
          eyebrow='Mood'
          title='How are you feeling?'
          apiError={mood.apiError}
        >
          <MoodForm
            memberId={memberId}
            submitting={mood.submitting}
            setSubmitting={mood.setSubmitting}
            onSuccess={mood.handleSuccess}
            onError={mood.setApiError}
            clearFeedback={mood.clearFeedback}
          />
        </LogCard>

        <LogCard
          eyebrow='Meal log'
          title='What did you eat?'
          apiError={meal.apiError}
          className='sm:col-span-3'
        >
          <MealForm
            memberId={memberId}
            submitting={meal.submitting}
            setSubmitting={meal.setSubmitting}
            onSuccess={meal.handleSuccess}
            onError={meal.setApiError}
            clearFeedback={meal.clearFeedback}
          />
        </LogCard>
      </div>
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </>
  );
}
