import { useCallback, useState } from 'react';
import LogCard from './quick-log/LogCard';
import MealForm from './quick-log/MealForm';
import MoodForm from './quick-log/MoodForm';
import SleepForm from './quick-log/SleepForm';
import WeightForm from './quick-log/WeightForm';
import { useCardFeedback } from './quick-log/useCardFeedback';
import ToastContainer from './Toast';
import { createToastId, type ToastItem } from './Toast.shared';

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

  const getFormProps = (feedback: typeof weight) => ({
    memberId,
    submitting: feedback.submitting,
    setSubmitting: feedback.setSubmitting,
    onSuccess: feedback.handleSuccess,
    onError: feedback.setApiError,
    clearFeedback: feedback.clearFeedback,
  });

  return (
    <>
      <div className='grid gap-4 grid-cols-1 sm:grid-cols-3'>
        <LogCard
          eyebrow='Weight'
          title='Track your weight'
          apiError={weight.apiError}
        >
          <WeightForm {...getFormProps(weight)} />
        </LogCard>

        <LogCard
          eyebrow='Sleep'
          title='How many hours?'
          apiError={sleep.apiError}
        >
          <SleepForm {...getFormProps(sleep)} />
        </LogCard>

        <LogCard
          eyebrow='Mood'
          title='How are you feeling?'
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
