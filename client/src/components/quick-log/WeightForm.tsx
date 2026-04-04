import { type FormEvent, useState } from 'react';
import { ApiError, postSignal } from '../../api/client';
import type { FormProps, WeightUnit } from './shared';
import {
  getRequestErrorMessage,
  getValidationMessage,
  INPUT_CLASSES,
  KG_TO_LB,
  parsePositiveNumber,
  PRIMARY_BUTTON_CLASSES,
} from './shared';

export default function WeightForm({
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
  const canSubmit = parsePositiveNumber(weight) !== null;

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
          {(['lb', 'kg'] as const).map((nextUnit) => (
            <button
              key={nextUnit}
              type='button'
              onClick={() => setUnit(nextUnit)}
              className={`rounded-full px-3 py-1 text-xs font-semibold transition ${
                unit === nextUnit
                  ? 'bg-[var(--color-primary)] text-white'
                  : 'bg-[var(--color-surface-soft)] text-[var(--color-muted)] hover:text-[var(--color-primary)]'
              }`}
            >
              {nextUnit}
            </button>
          ))}
        </div>
        {fieldError && (
          <p className='mt-2 text-sm text-[var(--color-error)]'>{fieldError}</p>
        )}
      </div>

      <button
        type='submit'
        disabled={submitting || !canSubmit}
        className={`mt-auto ${PRIMARY_BUTTON_CLASSES}`}
      >
        {submitting ? 'Saving…' : 'Log weight'}
      </button>
    </form>
  );
}
