import { type SyntheticEvent, useId, useState } from 'react';
import { ApiError, postSignal } from '../../api/client';
import type { MoodValue } from '../../types/member';
import type { FormProps } from './shared';
import {
  getRequestErrorMessage,
  getValidationMessage,
  MOOD_LABELS,
  MOOD_OPTIONS,
  PRIMARY_BUTTON_CLASSES,
} from './shared';
import MoodOption from './MoodOption';

export default function MoodForm({
  memberId,
  submitting,
  setSubmitting,
  onSuccess,
  onError,
  clearFeedback,
}: FormProps) {
  const groupId = useId();
  const [mood, setMood] = useState<MoodValue | null>(null);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const canSubmit = mood !== null;
  const fieldErrorId = fieldError ? `${groupId}-error` : undefined;

  function handleMoodSelect(nextMood: MoodValue) {
    setMood(nextMood);
    setFieldError(null);
  }

  async function handleSubmit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    clearFeedback();
    setFieldError(null);

    if (!mood) {
      setFieldError('Select a mood before submitting.');
      return;
    }

    setSubmitting(true);
    try {
      await postSignal(memberId, 'mood_logged', { mood });
      setMood(null);
      onSuccess(
        `Mood logged as ${MOOD_LABELS[mood].toLowerCase()} — thanks for checking in!`,
      );
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
      <fieldset aria-describedby={fieldErrorId} disabled={submitting}>
        <legend className='sr-only'>Mood</legend>
        <div className='flex items-center justify-center gap-5'>
          {MOOD_OPTIONS.map((option) => (
            <MoodOption
              key={option.value}
              option={option}
              groupName={`${groupId}-mood`}
              selected={mood === option.value}
              disabled={submitting}
              errorId={fieldErrorId}
              onSelect={handleMoodSelect}
            />
          ))}
        </div>
        {fieldError && (
          <p
            id={fieldErrorId}
            className='mt-2 text-sm text-[var(--color-error)]'
          >
            {fieldError}
          </p>
        )}
      </fieldset>
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
