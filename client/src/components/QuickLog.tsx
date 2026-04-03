import { useState, type FormEvent } from 'react';
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

type Tab = 'weight' | 'mood' | 'meal';
type MealField = 'meal_type' | 'carbs_g' | 'protein_g';
type MealFieldErrors = Partial<Record<MealField, string>>;

const TABS: Array<{ key: Tab; label: string }> = [
  { key: 'weight', label: 'Weight' },
  { key: 'mood', label: 'Mood' },
  { key: 'meal', label: 'Meal' },
];

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
      return 'We could not submit your update. Please try again.';
    }
  }

  return 'We could not submit your update. Please try again.';
}

export default function QuickLog({ memberId, onSignalSubmitted }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>('weight');
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  function clearFeedback() {
    setSuccess(null);
    setApiError(null);
  }

  return (
    <section
      aria-label='Log an update'
      className='bg-white rounded-xl border border-gray-200 shadow-sm'
    >
      <div className='px-6 pt-5 pb-2'>
        <h2 className='text-sm font-semibold text-gray-900 mb-3'>
          Quick log an update
        </h2>
        <div className='flex gap-1 border-b border-gray-200' role='tablist'>
          {TABS.map((tab) => (
            <button
              key={tab.key}
              role='tab'
              aria-selected={activeTab === tab.key}
              onClick={() => {
                setActiveTab(tab.key);
                clearFeedback();
              }}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px
                ${
                  activeTab === tab.key
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className='px-6 pb-5 pt-4'>
        {success && (
          <p
            role='status'
            className='text-sm text-green-700 bg-green-50 rounded-lg px-3 py-2 mb-3'
          >
            {success}
          </p>
        )}
        {apiError && (
          <p role='alert' className='text-sm text-red-600 mb-3'>
            {apiError}
          </p>
        )}

        {activeTab === 'weight' && (
          <WeightForm
            memberId={memberId}
            submitting={submitting}
            setSubmitting={setSubmitting}
            onSuccess={(message) => {
              setSuccess(message);
              onSignalSubmitted();
            }}
            onError={setApiError}
            clearFeedback={clearFeedback}
          />
        )}
        {activeTab === 'mood' && (
          <MoodForm
            memberId={memberId}
            submitting={submitting}
            setSubmitting={setSubmitting}
            onSuccess={(message) => {
              setSuccess(message);
              onSignalSubmitted();
            }}
            onError={setApiError}
            clearFeedback={clearFeedback}
          />
        )}
        {activeTab === 'meal' && (
          <MealForm
            memberId={memberId}
            submitting={submitting}
            setSubmitting={setSubmitting}
            onSuccess={(message) => {
              setSuccess(message);
              onSignalSubmitted();
            }}
            onError={setApiError}
            clearFeedback={clearFeedback}
          />
        )}
      </div>
    </section>
  );
}

function WeightForm({
  memberId,
  submitting,
  setSubmitting,
  onSuccess,
  onError,
  clearFeedback,
}: FormProps) {
  const [weight, setWeight] = useState('');
  const [fieldError, setFieldError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    clearFeedback();
    setFieldError(null);

    const parsedWeight = Number(weight);
    if (!Number.isFinite(parsedWeight) || parsedWeight <= 0) {
      setFieldError('Enter a weight greater than 0.');
      return;
    }

    setSubmitting(true);
    try {
      await postSignal(memberId, 'weight_logged', { weight_lb: parsedWeight });
      setWeight('');
      onSuccess('Weight logged.');
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
    <form onSubmit={handleSubmit} className='flex items-end gap-3'>
      <div className='flex-1'>
        <label
          htmlFor='weight-input'
          className='block text-sm text-gray-600 mb-1'
        >
          Weight (lb)
        </label>
        <input
          id='weight-input'
          type='number'
          step='0.1'
          min='0'
          value={weight}
          onChange={(event) => setWeight(event.target.value)}
          className='w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
          placeholder='e.g. 165'
        />
        {fieldError && (
          <p className='text-xs text-red-600 mt-1'>{fieldError}</p>
        )}
      </div>
      <button
        type='submit'
        disabled={submitting}
        className='px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors'
      >
        {submitting ? 'Saving…' : 'Log'}
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
      onSuccess('Mood logged.');
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
    <form onSubmit={handleSubmit} className='space-y-3'>
      <fieldset>
        <legend className='text-sm text-gray-600 mb-2'>
          How are you feeling?
        </legend>
        <div className='flex gap-2' role='radiogroup'>
          {MOOD_OPTIONS.map((option) => (
            <button
              key={option.value}
              type='button'
              role='radio'
              aria-checked={mood === option.value}
              onClick={() => setMood(option.value)}
              className={`flex-1 py-2 text-sm font-medium rounded-lg border transition-colors
                ${
                  mood === option.value
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                }`}
            >
              {option.label}
            </button>
          ))}
        </div>
        {fieldError && (
          <p className='text-xs text-red-600 mt-1'>{fieldError}</p>
        )}
      </fieldset>
      <div>
        <label htmlFor='mood-note' className='block text-sm text-gray-600 mb-1'>
          Note (optional)
        </label>
        <textarea
          id='mood-note'
          rows={2}
          value={note}
          onChange={(event) => setNote(event.target.value)}
          className='w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-none'
          placeholder='Anything you want to share...'
        />
      </div>
      <button
        type='submit'
        disabled={submitting}
        className='px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors'
      >
        {submitting ? 'Saving…' : 'Log mood'}
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
      onSuccess('Meal logged.');
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
    <form onSubmit={handleSubmit} className='space-y-3'>
      <div>
        <label htmlFor='meal-type' className='block text-sm text-gray-600 mb-1'>
          Meal type
        </label>
        <select
          id='meal-type'
          value={mealType}
          onChange={(event) => setMealType(event.target.value as MealType)}
          className='w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
        >
          {MEAL_TYPES.map((meal) => (
            <option key={meal.value} value={meal.value}>
              {meal.label}
            </option>
          ))}
        </select>
        {fieldErrors.meal_type && (
          <p className='text-xs text-red-600 mt-1'>{fieldErrors.meal_type}</p>
        )}
      </div>
      <div className='flex gap-3'>
        <div className='flex-1'>
          <label
            htmlFor='carbs-input'
            className='block text-sm text-gray-600 mb-1'
          >
            Carbs (g)
          </label>
          <input
            id='carbs-input'
            type='number'
            min='0'
            step='1'
            value={carbsG}
            onChange={(event) => setCarbsG(event.target.value)}
            className='w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
            placeholder='optional'
          />
          {fieldErrors.carbs_g && (
            <p className='text-xs text-red-600 mt-1'>{fieldErrors.carbs_g}</p>
          )}
        </div>
        <div className='flex-1'>
          <label
            htmlFor='protein-input'
            className='block text-sm text-gray-600 mb-1'
          >
            Protein (g)
          </label>
          <input
            id='protein-input'
            type='number'
            min='0'
            step='1'
            value={proteinG}
            onChange={(event) => setProteinG(event.target.value)}
            className='w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
            placeholder='optional'
          />
          {fieldErrors.protein_g && (
            <p className='text-xs text-red-600 mt-1'>{fieldErrors.protein_g}</p>
          )}
        </div>
      </div>
      <button
        type='submit'
        disabled={submitting}
        className='px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors'
      >
        {submitting ? 'Saving…' : 'Log meal'}
      </button>
    </form>
  );
}
