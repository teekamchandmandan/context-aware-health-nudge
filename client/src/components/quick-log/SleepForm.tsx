import { type SyntheticEvent, useState } from 'react';
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
  const parsedHours = parsePositiveNumber(hours, 24);
  const canSubmit = parsedHours !== null;

  async function handleSubmit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    clearFeedback();
    setFieldError(null);

    if (parsedHours === null) {
      setFieldError('Enter hours greater than 0 and up to 24.');
      return;
    }

    setSubmitting(true);
    try {
      await postSignal(memberId, 'sleep_logged', { sleep_hours: parsedHours });
      setHours('');
      onSuccess(
        `${parsedHours}h logged — sleep tracking helps us personalise your plan.`,
      );
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
        <div className='flex items-stretch gap-2'>
          <input
            id='sleep-input'
            name='sleep_hours'
            type='number'
            step='0.5'
            min='0.5'
            max='24'
            inputMode='decimal'
            autoComplete='off'
            value={hours}
            onChange={(event) => setHours(event.target.value)}
            className={`${INPUT_CLASSES} min-w-0 flex-1`}
            placeholder='e.g. 7.5'
          />
          <div className='shrink-0 inline-flex items-center rounded-[1rem] border border-[rgba(190,200,200,0.9)] bg-white px-3 py-3 text-sm font-semibold text-[var(--color-text)] shadow-[inset_0_1px_2px_rgba(25,28,29,0.03)]'>
            hours
          </div>
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
        {submitting ? 'Saving…' : 'Log sleep'}
      </button>
    </form>
  );
}
