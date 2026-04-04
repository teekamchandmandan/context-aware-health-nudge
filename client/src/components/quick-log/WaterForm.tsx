import { type FormEvent, useState } from 'react';
import { ApiError, postSignal } from '../../api/client';
import type { FormProps, WaterUnit } from './shared';
import {
  getRequestErrorMessage,
  getValidationMessage,
  INPUT_CLASSES,
  ML_PER_GLASS,
  parsePositiveNumber,
  PRIMARY_BUTTON_CLASSES,
} from './shared';

export default function WaterForm({
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
  const canSubmit = parsePositiveNumber(amount) !== null;

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
          {(['glasses', 'ml'] as const).map((nextUnit) => (
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
        {submitting ? 'Saving…' : 'Log water'}
      </button>
    </form>
  );
}
