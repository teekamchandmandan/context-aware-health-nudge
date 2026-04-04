import { type FormEvent, useState } from 'react';
import { ApiError, postSignal } from '../../api/client';
import type { FormProps } from './shared';
import {
  getRequestErrorMessage,
  getValidationMessage,
  INPUT_CLASSES,
  parsePositiveNumber,
  PRIMARY_BUTTON_CLASSES,
} from './shared';

export default function SleepForm({
  memberId,
  submitting,
  setSubmitting,
  onSuccess,
  onError,
  clearFeedback,
}: FormProps) {
  const [hours, setHours] = useState('');
  const [fieldError, setFieldError] = useState<string | null>(null);
  const parsedHours = parsePositiveNumber(hours);
  const canSubmit = parsedHours !== null && parsedHours <= 24;

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
        disabled={submitting || !canSubmit}
        className={`mt-auto ${PRIMARY_BUTTON_CLASSES}`}
      >
        {submitting ? 'Saving…' : 'Log sleep'}
      </button>
    </form>
  );
}
