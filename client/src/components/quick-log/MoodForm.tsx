import { type FormEvent, useState } from 'react';
import { ApiError, postSignal } from '../../api/client';
import type { MoodValue } from '../../types/member';
import type { FormProps } from './shared';
import {
  getRequestErrorMessage,
  getValidationMessage,
  INPUT_CLASSES,
  MOOD_OPTIONS,
  PRIMARY_BUTTON_CLASSES,
} from './shared';

export default function MoodForm({
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
  const canSubmit = mood !== null;

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
        disabled={submitting || !canSubmit}
        className={`mt-auto ${PRIMARY_BUTTON_CLASSES}`}
      >
        {submitting ? 'Saving…' : 'Log mood'}
      </button>
    </form>
  );
}
