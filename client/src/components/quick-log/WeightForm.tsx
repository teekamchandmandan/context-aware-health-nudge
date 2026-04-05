import { type SyntheticEvent, useState } from 'react';
import { ApiError, postSignal } from '../../api/client';
import type { FormProps, WeightUnit } from './shared';
import {
  getRequestErrorMessage,
  getValidationMessage,
  INPUT_CLASSES,
  KG_TO_LB,
  parsePositiveNumber,
  PRIMARY_BUTTON_CLASSES,
  SELECT_CLASSES,
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
  const parsedWeight = parsePositiveNumber(weight);
  const canSubmit = parsedWeight !== null;

  async function handleSubmit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    clearFeedback();
    setFieldError(null);

    if (parsedWeight === null) {
      setFieldError('Enter a weight greater than 0.');
      return;
    }

    const weightLb =
      unit === 'kg'
        ? Math.round(parsedWeight * KG_TO_LB * 10) / 10
        : parsedWeight;

    setSubmitting(true);
    try {
      await postSignal(memberId, 'weight_logged', { weight_lb: weightLb });
      setWeight('');
      onSuccess(`${parsedWeight} ${unit} logged — nice work staying on track!`);
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
        <div className='flex items-stretch gap-2'>
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
            className={`${INPUT_CLASSES} min-w-0 flex-1`}
            placeholder={unit === 'lb' ? 'e.g. 165' : 'e.g. 75'}
          />
          <label className='sr-only' htmlFor='weight-unit'>
            Weight unit
          </label>
          <select
            id='weight-unit'
            name='weight_unit'
            value={unit}
            onChange={(event) => setUnit(event.target.value as WeightUnit)}
            className={SELECT_CLASSES}
          >
            <option value='lb'>lb</option>
            <option value='kg'>kg</option>
          </select>
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
