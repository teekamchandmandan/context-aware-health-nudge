import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react';
import { ApiError, postMealLog } from '../../api/client';
import type { FormProps, MealFieldErrors } from './shared';
import {
  getRequestErrorMessage,
  getValidationMessage,
  INPUT_CLASSES,
  PRIMARY_BUTTON_CLASSES,
} from './shared';

export default function MealForm({
  memberId,
  submitting,
  setSubmitting,
  onSuccess,
  onError,
  clearFeedback,
}: FormProps) {
  const [description, setDescription] = useState('');
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreviewUrl, setPhotoPreviewUrl] = useState<string | null>(null);
  const [photoInputKey, setPhotoInputKey] = useState(0);
  const [fieldErrors, setFieldErrors] = useState<MealFieldErrors>({});
  const canSubmit = description.trim().length > 0 || photoFile !== null;

  useEffect(() => {
    return () => {
      if (photoPreviewUrl) {
        URL.revokeObjectURL(photoPreviewUrl);
      }
    };
  }, [photoPreviewUrl]);

  function clearPhotoSelection() {
    if (photoPreviewUrl) {
      URL.revokeObjectURL(photoPreviewUrl);
    }
    setPhotoPreviewUrl(null);
    setPhotoFile(null);
    setPhotoInputKey((value) => value + 1);
  }

  function handleDescriptionChange(event: ChangeEvent<HTMLTextAreaElement>) {
    setDescription(event.target.value);
    setFieldErrors((current) => ({ ...current, description: undefined }));
  }

  function handlePhotoChange(event: ChangeEvent<HTMLInputElement>) {
    const nextFile = event.target.files?.[0] ?? null;
    if (photoPreviewUrl) {
      URL.revokeObjectURL(photoPreviewUrl);
    }
    setPhotoFile(nextFile);
    setPhotoPreviewUrl(nextFile ? URL.createObjectURL(nextFile) : null);
    setFieldErrors((current) => ({ ...current, photo: undefined }));
  }

  function mapMealValidationMessage(validationMessage: string) {
    if (validationMessage.includes('description or photo')) {
      setFieldErrors({ description: 'Add meal details or upload a photo.' });
      return true;
    }

    if (validationMessage.includes('image')) {
      setFieldErrors({ photo: 'Upload an image file for meal photos.' });
      return true;
    }

    return false;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    clearFeedback();
    setFieldErrors({});

    if (!canSubmit) {
      setFieldErrors({ description: 'Add meal details or upload a photo.' });
      return;
    }

    const formData = new FormData();
    if (description.trim()) {
      formData.append('description', description.trim());
    }
    if (photoFile) {
      formData.append('photo', photoFile);
    }

    setSubmitting(true);
    try {
      await postMealLog(memberId, formData);
      setDescription('');
      clearPhotoSelection();
      setFieldErrors({});
      onSuccess('Your meal has been saved.');
    } catch (error) {
      if (error instanceof ApiError && error.status === 422) {
        const validationMessage =
          getValidationMessage(error) ??
          'Check your meal details and try again.';

        if (!mapMealValidationMessage(validationMessage)) {
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
          htmlFor='meal-description'
          className='mb-2 block text-sm font-medium text-[var(--color-muted)]'
        >
          Meal details
        </label>
        <textarea
          id='meal-description'
          name='meal_description'
          rows={4}
          autoComplete='off'
          value={description}
          onChange={handleDescriptionChange}
          className={`${INPUT_CLASSES} resize-none`}
          placeholder='Describe what you ate, or just upload a photo.'
        />
        {fieldErrors.description && (
          <p className='mt-2 text-sm text-[var(--color-error)]'>
            {fieldErrors.description}
          </p>
        )}
      </div>

      <div>
        <label
          htmlFor='meal-photo'
          className='mb-2 block text-sm font-medium text-[var(--color-muted)]'
        >
          Photo (optional)
        </label>
        <input
          key={photoInputKey}
          id='meal-photo'
          name='meal_photo'
          type='file'
          accept='image/*'
          onChange={handlePhotoChange}
          className='block w-full rounded-[1rem] border border-dashed border-[rgba(190,200,200,0.9)] bg-white px-4 py-3 text-sm text-[var(--color-text)] file:mr-3 file:rounded-full file:border-0 file:bg-[rgba(168,239,239,0.18)] file:px-3 file:py-2 file:text-sm file:font-semibold file:text-[var(--color-primary)]'
        />
        {fieldErrors.photo && (
          <p className='mt-2 text-sm text-[var(--color-error)]'>
            {fieldErrors.photo}
          </p>
        )}
      </div>

      {photoPreviewUrl && (
        <div className='rounded-[1.25rem] border border-[rgba(190,200,200,0.75)] bg-[rgba(247,250,250,0.92)] p-4'>
          <div className='flex items-start justify-between gap-3'>
            <div>
              <p className='text-sm font-semibold text-[var(--color-primary)]'>
                Image preview
              </p>
              <p className='mt-1 text-xs text-[var(--color-muted)]'>
                {photoFile?.name ?? 'Selected photo'}
              </p>
            </div>
            <button
              type='button'
              onClick={clearPhotoSelection}
              className='text-xs font-semibold text-[var(--color-primary)] transition hover:text-[var(--color-primary-strong)]'
            >
              Remove photo
            </button>
          </div>
          <img
            src={photoPreviewUrl}
            alt='Preview of the selected meal photo'
            className='mt-4 h-48 w-full rounded-[1rem] object-cover'
          />
        </div>
      )}

      <button
        type='submit'
        disabled={submitting || !canSubmit}
        className={`mt-auto ${PRIMARY_BUTTON_CLASSES}`}
      >
        {submitting ? 'Saving…' : 'Log meal'}
      </button>
    </form>
  );
}
