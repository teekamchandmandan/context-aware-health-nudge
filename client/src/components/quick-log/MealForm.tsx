import {
  useEffect,
  useState,
  type ChangeEvent,
  type DragEvent,
  type FormEvent,
} from 'react';
import { ApiError, postMealLog } from '../../api/client';
import type { FormProps, MealFieldErrors } from './shared';
import {
  getRequestErrorMessage,
  getValidationMessage,
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
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreviewUrl, setPhotoPreviewUrl] = useState<string | null>(null);
  const [photoInputKey, setPhotoInputKey] = useState(0);
  const [dragging, setDragging] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<MealFieldErrors>({});
  const canSubmit = photoFile !== null;

  useEffect(() => {
    return () => {
      if (photoPreviewUrl) {
        URL.revokeObjectURL(photoPreviewUrl);
      }
    };
  }, [photoPreviewUrl]);

  function acceptFile(file: File | null) {
    if (photoPreviewUrl) {
      URL.revokeObjectURL(photoPreviewUrl);
    }
    setPhotoFile(file);
    setPhotoPreviewUrl(file ? URL.createObjectURL(file) : null);
    setFieldErrors({});
  }

  function clearPhotoSelection() {
    acceptFile(null);
    setPhotoInputKey((value) => value + 1);
  }

  function handlePhotoChange(event: ChangeEvent<HTMLInputElement>) {
    acceptFile(event.target.files?.[0] ?? null);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    const file = event.dataTransfer.files?.[0] ?? null;
    if (file && file.type.startsWith('image/')) {
      acceptFile(file);
    } else {
      setFieldErrors({ photo: 'Please drop an image file.' });
    }
  }

  function handleDragOver(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(true);
  }

  function handleDragLeave() {
    setDragging(false);
  }

  function getPhotoValidationError(validationMessage: string): string | null {
    if (validationMessage.includes('meal photo')) {
      return 'Add a photo of your meal.';
    }

    if (validationMessage.includes('image')) {
      return 'Upload an image file for meal photos.';
    }

    return null;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    clearFeedback();
    setFieldErrors({});

    if (!canSubmit) {
      setFieldErrors({ photo: 'Add a photo of your meal.' });
      return;
    }

    const formData = new FormData();
    if (photoFile) {
      formData.append('photo', photoFile);
    }

    setSubmitting(true);
    try {
      await postMealLog(memberId, formData);
      clearPhotoSelection();
      setFieldErrors({});
      onSuccess('Your meal has been saved.');
    } catch (error) {
      if (error instanceof ApiError && error.status === 422) {
        const validationMessage =
          getValidationMessage(error) ?? 'Check your photo and try again.';
        const photoError = getPhotoValidationError(validationMessage);

        if (photoError) {
          setFieldErrors({ photo: photoError });
          return;
        }

        onError(validationMessage);
        return;
      }

      onError(getRequestErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className='mt-2 flex flex-1 flex-col gap-4'>
      {!photoPreviewUrl && (
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          className={`flex flex-col items-center justify-center rounded-[1.25rem] border-2 border-dashed px-6 py-10 text-center transition ${
            dragging
              ? 'border-[var(--color-primary)] bg-[rgba(168,239,239,0.12)]'
              : 'border-[rgba(190,200,200,0.7)] bg-[rgba(247,250,250,0.5)]'
          }`}
        >
          <div className='mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-[rgba(190,200,200,0.2)] text-lg text-[var(--color-muted)]'>
            <span aria-hidden='true'>📷</span>
          </div>
          <p className='text-sm font-semibold text-[var(--color-text)]'>
            Add a photo of your meal
          </p>
          <p className='mt-1 text-xs text-[var(--color-muted)]'>
            or choose from your gallery
          </p>
          <label
            htmlFor='meal-photo'
            className='mt-4 inline-flex cursor-pointer items-center justify-center rounded-full border border-[var(--color-primary)] px-5 py-2 text-sm font-semibold text-[var(--color-primary)] transition hover:bg-[rgba(168,239,239,0.12)]'
          >
            Choose photo
          </label>
          <input
            key={photoInputKey}
            id='meal-photo'
            name='meal_photo'
            type='file'
            accept='image/*'
            onChange={handlePhotoChange}
            className='sr-only'
          />
          {fieldErrors.photo && (
            <p className='mt-3 text-sm text-[var(--color-error)]'>
              {fieldErrors.photo}
            </p>
          )}
        </div>
      )}

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
