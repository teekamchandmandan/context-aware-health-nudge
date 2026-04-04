import LogCard from './quick-log/LogCard';
import MealForm from './quick-log/MealForm';
import MoodForm from './quick-log/MoodForm';
import SleepForm from './quick-log/SleepForm';
import WaterForm from './quick-log/WaterForm';
import WeightForm from './quick-log/WeightForm';
import { useCardFeedback } from './quick-log/useCardFeedback';

interface Props {
  memberId: string;
  onSignalSubmitted: () => void;
}

export default function QuickLog({ memberId, onSignalSubmitted }: Props) {
  const weight = useCardFeedback(onSignalSubmitted);
  const mood = useCardFeedback(onSignalSubmitted);
  const meal = useCardFeedback(onSignalSubmitted);
  const water = useCardFeedback(onSignalSubmitted);
  const sleep = useCardFeedback(onSignalSubmitted);

  return (
    <div className='grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-6'>
      <LogCard
        eyebrow='Weight'
        title='Log your weight'
        success={weight.success}
        apiError={weight.apiError}
        className='lg:col-span-2'
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
        eyebrow='Water'
        title='Track your hydration'
        success={water.success}
        apiError={water.apiError}
        className='lg:col-span-2'
      >
        <WaterForm
          memberId={memberId}
          submitting={water.submitting}
          setSubmitting={water.setSubmitting}
          onSuccess={water.handleSuccess}
          onError={water.setApiError}
          clearFeedback={water.clearFeedback}
        />
      </LogCard>

      <LogCard
        eyebrow='Sleep'
        title='How did you sleep?'
        success={sleep.success}
        apiError={sleep.apiError}
        className='lg:col-span-2'
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
        success={mood.success}
        apiError={mood.apiError}
        className='lg:col-span-3'
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
        eyebrow='Meal'
        title='Log what you ate'
        success={meal.success}
        apiError={meal.apiError}
        className='lg:col-span-3'
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
  );
}
