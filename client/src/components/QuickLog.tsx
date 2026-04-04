import { useState, type FormEvent, type ReactNode } from 'react';
import { postSignal, ApiError } from '../api/client';
import type { MealType, MoodValue } from '../types/member';

interface Props {
  memberId: string;
  onSignalSubmitted: () => void;
}

interface FormProps {
  memberId: string;
  submitting: boolean;
  setSubmitting: (value: boolean) => void;
  onSuccess: (message: string) => void;
  onError: (message: string) => void;
  clearFeedback: () => void;
}

type MealField = 'meal_type' | 'carbs_g' | 'protein_g';
type MealFieldErrors = Partial<Record<MealField, string>>;

const MOOD_OPTIONS: Array<{ value: MoodValue; label: string }> = [
  { value: 'low', label: 'Low' },
  { value: 'neutral', label: 'Neutral' },
  { value: 'high', label: 'High' },
];

const MEAL_TYPES: Array<{ value: MealType; label: string }> = [
  { value: 'breakfast', label: 'Breakfast' },
  { value: 'lunch', label: 'Lunch' },
  { value: 'dinner', label: 'Dinner' },
  { value: 'snack', label: 'Snack' },
];

const INPUT_CLASSES =
  'w-full rounded-[1rem] border border-[rgba(190,200,200,0.9)] bg-white px-4 py-3 text-sm text-[var(--color-text)] shadow-[inset_0_1px_2px_rgba(25,28,29,0.03)] transition focus:border-[var(--color-primary-strong)] focus:outline-none focus:ring-4 focus:ring-[rgba(168,239,239,0.45)]';

const PRIMARY_BUTTON_CLASSES =
  'inline-flex items-center justify-center rounded-[1rem] bg-[var(--color-primary)] px-5 py-3 text-sm font-semibold text-white shadow-[0_16px_36px_rgba(0,66,66,0.18)] transition hover:-translate-y-0.5 hover:bg-[var(--color-primary-strong)] disabled:cursor-not-allowed disabled:opacity-60';

function getValidationMessage(error: ApiError): string | null {
  if (typeof error.body === 'object' && error.body && 'detail' in error.body) {
    const detail = error.body.detail;

    if (typeof detail === 'string') {
      return detail;
    }

    if (Array.isArray(detail)) {
      const first = detail[0];
      if (first && typeof first === 'object' && 'msg' in first) {
        const message = first.msg;
        return typeof message === 'string' ? message : null;
      }
    }
  }

  return null;
}

function getRequestErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 404) {
      console.error('Signal endpoint returned 404', error.body);
    }

    if (error.status === 0 || error.status === 404 || error.status >= 500) {
      return 'We could not save that. Please try again.';
    }
  }

  return 'We could not save that. Please try again.';
}

function LogCard({
  eyebrow,
  title,
  children,
  success,
  apiError,
  className,
}: {
  eyebrow: string;
  title: string;
  children: ReactNode;
  success: string | null;
  apiError: string | null;
  className?: string;
}) {
  return (
    <section
      aria-label={`Log ${eyebrow.toLowerCase()}`}
      className={`flex flex-col rounded-[2rem] border border-white/70 bg-[rgba(255,255,255,0.82)] p-5 shadow-[0_24px_80px_rgba(11,33,33,0.08)] backdrop-blur-xl sm:p-6 ${className ?? ''}`}
    >
      <p className='text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-muted)]'>
        {eyebrow}
      </p>
      <h3 className='mt-1 font-headline text-lg font-bold tracking-[-0.04em] text-[var(--color-primary)]'>
        {title}
      </h3>

      {success && (
        <p
          role='status'
          className='mt-3 rounded-[1rem] bg-[rgba(143,246,208,0.22)] px-4 py-3 text-sm font-medium text-[var(--color-accent)]'
        >
          {success}
        </p>
      )}
      {apiError && (
        <p
          role='alert'
          className='mt-3 rounded-[1rem] bg-[#fff0ee] px-4 py-3 text-sm font-medium text-[var(--color-error)]'
        >
          {apiError}
        </p>
      )}

      <div className='mt-4 flex flex-1 flex-col'>{children}</div>
    </section>
  );
}

function useCardFeedback(onSignalSubmitted: () => void) {
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  function clearFeedback() {
    setSuccess(null);
    setApiError(null);
  }

  function handleSuccess(message: string) {
    setSuccess(message);
    onSignalSubmitted();
  }

  return {
    submitting,
    setSubmitting,
    success,
    apiError,
    setApiError,
    clearFeedback,
    handleSuccess,
  };
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

type WeightUnit = 'lb' | 'kg';
const KG_TO_LB = 2.20462;

function WeightForm({
  memberId,
  submitting,
  setSubmitting,
  onSuccess,
  onError,
  clearFeedback,
}: FormProps) {
  const [weight, setWeight] = useState('');
  const [unit, setUnit] = useState<WeightUnit>('lb');
  const [fieldError, setFieldError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    clearFeedback();
    setFieldError(null);

    const parsed = Number(weight);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      setFieldError('Enter a weight greater than 0.');
      return;
    }

    const weightLb =
      unit === 'kg' ? Math.round(parsed * KG_TO_LB * 10) / 10 : parsed;

    setSubmitting(true);
    try {
      await postSignal(memberId, 'weight_logged', { weight_lb: weightLb });
      setWeight('');
      onSuccess('Your weight has been saved.');
    } catch (error) {
      if (error instanceof ApiError && error.status === 422) {
        setFieldError(getValidationMessage(error) ?? 'Enter a valid weight.');
        return;
      }

      onError(getRequestErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className='flex flex-1 flex-col gap-4'>
      <div>
        <label
          htmlFor='weight-input'
          className='mb-2 block text-sm font-medium text-[var(--color-muted)]'
        >
          Weight
        </label>
        <input
          id='weight-input'
          name='weight'
          type='number'
          step='0.1'
          min='0'
          inputMode='decimal'
          autoComplete='off'
          value={weight}
          onChange={(event) => setWeight(event.target.value)}
          className={INPUT_CLASSES}
          placeholder={unit === 'lb' ? 'e.g. 165' : 'e.g. 75'}
        />
        <div className='mt-2 flex gap-2'>
          {(['lb', 'kg'] as const).map((u) => (
            <button
              key={u}
              type='button'
              onClick={() => setUnit(u)}
              className={`rounded-full px-3 py-1 text-xs font-semibold transition ${
                unit === u
                  ? 'bg-[var(--color-primary)] text-white'
                  : 'bg-[var(--color-surface-soft)] text-[var(--color-muted)] hover:text-[var(--color-primary)]'
              }`}
            >
              {u}
            </button>
          ))}
        </div>
        {fieldError && (
          <p className='mt-2 text-sm text-[var(--color-error)]'>{fieldError}</p>
        )}
      </div>

      <button
        type='submit'
        disabled={submitting}
        className={`mt-auto ${PRIMARY_BUTTON_CLASSES}`}
      >
        {submitting ? 'Saving…' : 'Save weight'}
      </button>
    </form>
  );
}

function MoodForm({
  memberId,
  submitting,
  setSubmitting,
  onSuccess,
  onError,
  clearFeedback,
}: FormProps) {
  const [mood, setMood] = useState<MoodValue | null>(null);
  const [note, setNote] = useState('');
  const [fieldError, setFieldError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    clearFeedback();
    setFieldError(null);

    if (!mood) {
      setFieldError('Select a mood before submitting.');
      return;
    }

    setSubmitting(true);
    try {
      const payload: Record<string, unknown> = { mood };
      if (note.trim()) {
        payload.note = note.trim();
      }

      await postSignal(memberId, 'mood_logged', payload);
      setMood(null);
      setNote('');
      onSuccess('Your update has been saved.');
    } catch (error) {
      if (error instanceof ApiError && error.status === 422) {
        setFieldError(getValidationMessage(error) ?? 'Select a valid mood.');
        return;
      }

      onError(getRequestErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className='flex flex-1 flex-col gap-4'>
      <fieldset>
        <legend className='mb-2 text-sm font-medium text-[var(--color-muted)]'>
          Pick one
        </legend>
        <div className='grid grid-cols-3 gap-2'>
          {MOOD_OPTIONS.map((option) => (
            <label
              key={option.value}
              className={`cursor-pointer rounded-[1rem] border px-3 py-3 text-center text-sm font-semibold transition ${
                mood === option.value
                  ? 'border-[var(--color-primary)] bg-[var(--color-primary)] text-white shadow-[0_14px_30px_rgba(0,66,66,0.16)]'
                  : 'border-[rgba(190,200,200,0.9)] bg-white text-[var(--color-text)] hover:border-[var(--color-primary)] hover:bg-[rgba(168,239,239,0.12)]'
              }`}
            >
              <input
                type='radio'
                name='mood'
                value={option.value}
                checked={mood === option.value}
                onChange={() => setMood(option.value)}
                className='sr-only'
              />
              <span>{option.label}</span>
            </label>
          ))}
        </div>
        {fieldError && (
          <p className='mt-2 text-sm text-[var(--color-error)]'>{fieldError}</p>
        )}
      </fieldset>
      <div>
        <label
          htmlFor='mood-note'
          className='mb-2 block text-sm font-medium text-[var(--color-muted)]'
        >
          Add a note (optional)
        </label>
        <textarea
          id='mood-note'
          name='mood_note'
          rows={6}
          autoComplete='off'
          value={note}
          onChange={(event) => setNote(event.target.value)}
          className={`${INPUT_CLASSES} resize-none`}
          placeholder='Anything you want to share…'
        />
      </div>
      <button
        type='submit'
        disabled={submitting}
        className={`mt-auto ${PRIMARY_BUTTON_CLASSES}`}
      >
        {submitting ? 'Saving…' : 'Save mood'}
      </button>
    </form>
  );
}

function MealForm({
  memberId,
  submitting,
  setSubmitting,
  onSuccess,
  onError,
  clearFeedback,
}: FormProps) {
  const [mealType, setMealType] = useState<MealType>('breakfast');
  const [carbsG, setCarbsG] = useState('');
  const [proteinG, setProteinG] = useState('');
  const [fieldErrors, setFieldErrors] = useState<MealFieldErrors>({});

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    clearFeedback();
    setFieldErrors({});

    const nextErrors: MealFieldErrors = {};
    const parsedCarbs = carbsG.trim() === '' ? null : Number(carbsG);
    const parsedProtein = proteinG.trim() === '' ? null : Number(proteinG);

    if (
      parsedCarbs !== null &&
      (!Number.isFinite(parsedCarbs) || parsedCarbs < 0)
    ) {
      nextErrors.carbs_g = 'Enter carbs as 0 or more, or leave it blank.';
    }

    if (
      parsedProtein !== null &&
      (!Number.isFinite(parsedProtein) || parsedProtein < 0)
    ) {
      nextErrors.protein_g = 'Enter protein as 0 or more, or leave it blank.';
    }

    if (Object.keys(nextErrors).length > 0) {
      setFieldErrors(nextErrors);
      return;
    }

    const payload: Record<string, unknown> = {
      meal_type: mealType,
      photo_attached: false,
    };

    if (parsedCarbs !== null) {
      payload.carbs_g = parsedCarbs;
    } else {
      payload.meal_tag = mealType;
    }

    if (parsedProtein !== null) {
      payload.protein_g = parsedProtein;
    }

    setSubmitting(true);
    try {
      await postSignal(memberId, 'meal_logged', payload);
      setCarbsG('');
      setProteinG('');
      setFieldErrors({});
      onSuccess('Your meal has been saved.');
    } catch (error) {
      if (error instanceof ApiError && error.status === 422) {
        const validationMessage =
          getValidationMessage(error) ??
          'Check your meal details and try again.';
        const backendErrors: MealFieldErrors = {};

        if (validationMessage.includes('meal_type')) {
          backendErrors.meal_type = 'Select a meal type.';
        }
        if (
          validationMessage.includes('carbs_g') ||
          validationMessage.includes('meal_tag')
        ) {
          backendErrors.carbs_g =
            'Add carbs or leave the field blank to use the meal type fallback.';
        }

        if (Object.keys(backendErrors).length > 0) {
          setFieldErrors(backendErrors);
        } else {
          onError(validationMessage);
        }
        return;
      }

      onError(getRequestErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className='flex flex-1 flex-col gap-4'>
      <div>
        <label
          htmlFor='meal-type'
          className='mb-2 block text-sm font-medium text-[var(--color-muted)]'
        >
          Meal
        </label>
        <select
          id='meal-type'
          name='meal_type'
          autoComplete='off'
          value={mealType}
          onChange={(event) => setMealType(event.target.value as MealType)}
          className={INPUT_CLASSES}
        >
          {MEAL_TYPES.map((meal) => (
            <option key={meal.value} value={meal.value}>
              {meal.label}
            </option>
          ))}
        </select>
        {fieldErrors.meal_type && (
          <p className='mt-2 text-sm text-[var(--color-error)]'>
            {fieldErrors.meal_type}
          </p>
        )}
      </div>
      <div className='grid gap-3'>
        <div className='flex-1'>
          <label
            htmlFor='carbs-input'
            className='mb-2 block text-sm font-medium text-[var(--color-muted)]'
          >
            Carbs (g)
          </label>
          <input
            id='carbs-input'
            name='carbs_g'
            type='number'
            min='0'
            step='1'
            inputMode='numeric'
            autoComplete='off'
            value={carbsG}
            onChange={(event) => setCarbsG(event.target.value)}
            className={INPUT_CLASSES}
            placeholder='Optional…'
          />
          {fieldErrors.carbs_g && (
            <p className='mt-2 text-sm text-[var(--color-error)]'>
              {fieldErrors.carbs_g}
            </p>
          )}
        </div>
        <div className='flex-1'>
          <label
            htmlFor='protein-input'
            className='mb-2 block text-sm font-medium text-[var(--color-muted)]'
          >
            Protein (g)
          </label>
          <input
            id='protein-input'
            name='protein_g'
            type='number'
            min='0'
            step='1'
            inputMode='numeric'
            autoComplete='off'
            value={proteinG}
            onChange={(event) => setProteinG(event.target.value)}
            className={INPUT_CLASSES}
            placeholder='Optional…'
          />
          {fieldErrors.protein_g && (
            <p className='mt-2 text-sm text-[var(--color-error)]'>
              {fieldErrors.protein_g}
            </p>
          )}
        </div>
      </div>
      <p className='text-xs text-[var(--color-muted)]'>
        Leave carbs blank if you’re not sure.
      </p>
      <button
        type='submit'
        disabled={submitting}
        className={`mt-auto ${PRIMARY_BUTTON_CLASSES}`}
      >
        {submitting ? 'Saving…' : 'Save meal'}
      </button>
    </form>
  );
}
type WaterUnit = 'ml' | 'glasses';
const ML_PER_GLASS = 250;

function WaterForm({
  memberId,
  submitting,
  setSubmitting,
  onSuccess,
  onError,
  clearFeedback,
}: FormProps) {
  const [amount, setAmount] = useState('');
  const [unit, setUnit] = useState<WaterUnit>('glasses');
  const [fieldError, setFieldError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    clearFeedback();
    setFieldError(null);

    const parsed = Number(amount);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      setFieldError('Enter an amount greater than 0.');
      return;
    }

    const waterMl =
      unit === 'glasses' ? Math.round(parsed * ML_PER_GLASS) : parsed;

    setSubmitting(true);
    try {
      await postSignal(memberId, 'water_logged', { water_ml: waterMl });
      setAmount('');
      onSuccess('Your water intake has been saved.');
    } catch (error) {
      if (error instanceof ApiError && error.status === 422) {
        setFieldError(getValidationMessage(error) ?? 'Enter a valid amount.');
        return;
      }

      onError(getRequestErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className='flex flex-1 flex-col gap-4'>
      <div>
        <label
          htmlFor='water-input'
          className='mb-2 block text-sm font-medium text-[var(--color-muted)]'
        >
          Amount
        </label>
        <input
          id='water-input'
          name='water'
          type='number'
          step={unit === 'glasses' ? '1' : '50'}
          min='0'
          inputMode='decimal'
          autoComplete='off'
          value={amount}
          onChange={(event) => setAmount(event.target.value)}
          className={INPUT_CLASSES}
          placeholder={unit === 'glasses' ? 'e.g. 4' : 'e.g. 500'}
        />
        <div className='mt-2 flex gap-2'>
          {(['glasses', 'ml'] as const).map((u) => (
            <button
              key={u}
              type='button'
              onClick={() => setUnit(u)}
              className={`rounded-full px-3 py-1 text-xs font-semibold transition ${
                unit === u
                  ? 'bg-[var(--color-primary)] text-white'
                  : 'bg-[var(--color-surface-soft)] text-[var(--color-muted)] hover:text-[var(--color-primary)]'
              }`}
            >
              {u}
            </button>
          ))}
        </div>
        {fieldError && (
          <p className='mt-2 text-sm text-[var(--color-error)]'>{fieldError}</p>
        )}
      </div>

      <button
        type='submit'
        disabled={submitting}
        className={`mt-auto ${PRIMARY_BUTTON_CLASSES}`}
      >
        {submitting ? 'Saving…' : 'Save water'}
      </button>
    </form>
  );
}

function SleepForm({
  memberId,
  submitting,
  setSubmitting,
  onSuccess,
  onError,
  clearFeedback,
}: FormProps) {
  const [hours, setHours] = useState('');
  const [fieldError, setFieldError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    clearFeedback();
    setFieldError(null);

    const parsed = Number(hours);
    if (!Number.isFinite(parsed) || parsed <= 0 || parsed > 24) {
      setFieldError('Enter hours between 0 and 24.');
      return;
    }

    setSubmitting(true);
    try {
      await postSignal(memberId, 'sleep_logged', { sleep_hours: parsed });
      setHours('');
      onSuccess('Your sleep has been saved.');
    } catch (error) {
      if (error instanceof ApiError && error.status === 422) {
        setFieldError(
          getValidationMessage(error) ?? 'Enter valid sleep hours.',
        );
        return;
      }

      onError(getRequestErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className='flex flex-1 flex-col gap-4'>
      <div>
        <label
          htmlFor='sleep-input'
          className='mb-2 block text-sm font-medium text-[var(--color-muted)]'
        >
          Hours slept
        </label>
        <input
          id='sleep-input'
          name='sleep_hours'
          type='number'
          step='0.5'
          min='0'
          max='24'
          inputMode='decimal'
          autoComplete='off'
          value={hours}
          onChange={(event) => setHours(event.target.value)}
          className={INPUT_CLASSES}
          placeholder='e.g. 7.5'
        />
        {fieldError && (
          <p className='mt-2 text-sm text-[var(--color-error)]'>{fieldError}</p>
        )}
      </div>

      <button
        type='submit'
        disabled={submitting}
        className={`mt-auto ${PRIMARY_BUTTON_CLASSES}`}
      >
        {submitting ? 'Saving…' : 'Save sleep'}
      </button>
    </form>
  );
}
