import {
  useEffect,
  useState,
  type ChangeEvent,
  type DragEvent,
  type SyntheticEvent,
} from 'react';
import { ApiError, postMealLog } from '../../api/client';
import type { FormProps, MealFieldErrors } from './shared';
import {
  getRequestErrorMessage,
  getValidationMessage,
  PRIMARY_BUTTON_CLASSES,
} from './shared';

const CAMERA_ICON_PROPS = {
  width: 28,
  height: 28,
  viewBox: '0 0 28 28',
  fill: 'none',
  'aria-hidden': true,
} as const;

function CameraUploadIcon() {
  return (
    <svg {...CAMERA_ICON_PROPS}>
      <circle cx='14' cy='14' r='11' fill='rgba(168,239,239,0.3)' />
      <path
        d='M9.4 10.35h2.2l1.05-1.7h2.7l1.05 1.7h2.2c1 0 1.8.8 1.8 1.8v6.1c0 1-.8 1.8-1.8 1.8H9.4c-1 0-1.8-.8-1.8-1.8v-6.1c0-1 .8-1.8 1.8-1.8Z'
        stroke='var(--color-primary)'
        strokeWidth='1.8'
        strokeLinecap='round'
        strokeLinejoin='round'
        fill='rgba(255,255,255,0.88)'
      />
      <circle
        cx='14'
        cy='15.1'
        r='3.1'
        stroke='var(--color-primary)'
        strokeWidth='1.8'
      />
      <circle cx='18.25' cy='12.55' r='0.9' fill='var(--color-primary)' />
    </svg>
  );
}

const SUPPORTED_MEAL_PHOTO_TYPES = new Set([
  'image/png',
  'image/jpeg',
  'image/jpg',
  'image/gif',
  'image/webp',
]);
const SUPPORTED_MEAL_PHOTO_EXTENSIONS = [
  '.png',
  '.jpg',
  '.jpeg',
  '.gif',
  '.webp',
];
const SUPPORTED_MEAL_PHOTO_ACCEPT =
  'image/png,image/jpeg,image/jpg,image/gif,image/webp';
const SUPPORTED_MEAL_PHOTO_MESSAGE = 'PNG, JPEG, GIF, or WEBP up to 10 MB.';
const INVALID_PHOTO_MESSAGE = 'Upload a PNG, JPEG, GIF, or WEBP image.';
const INVALID_DROP_MESSAGE = 'Please drop a PNG, JPEG, GIF, or WEBP image.';

function isSupportedMealPhoto(file: File): boolean {
  const normalizedType = file.type.trim().toLowerCase();
  if (normalizedType && SUPPORTED_MEAL_PHOTO_TYPES.has(normalizedType)) {
    return true;
  }

  const normalizedName = file.name.trim().toLowerCase();
  return SUPPORTED_MEAL_PHOTO_EXTENSIONS.some((extension) =>
    normalizedName.endsWith(extension),
  );
}

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
    handlePhotoSelection(event.target.files?.[0] ?? null);
  }

  function handlePhotoSelection(
    file: File | null,
    missingFileMessage?: string,
  ) {
    if (!file) {
      if (missingFileMessage) {
        setFieldErrors({ photo: missingFileMessage });
        return;
      }

      acceptFile(null);
      return;
    }

    if (!isSupportedMealPhoto(file)) {
      setFieldErrors({ photo: INVALID_PHOTO_MESSAGE });
      return;
    }

    acceptFile(file);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    handlePhotoSelection(
      event.dataTransfer.files?.[0] ?? null,
      INVALID_DROP_MESSAGE,
    );
  }

  function handleDragOver(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(true);
  }

  function handleDragLeave() {
    setDragging(false);
  }

  function getPhotoValidationError(validationMessage: string): string | null {
    if (
      validationMessage.includes('PNG, JPEG, GIF, or WEBP') ||
      validationMessage.includes('meal photo must be a PNG')
    ) {
      return INVALID_PHOTO_MESSAGE;
    }

    if (validationMessage.includes('requires a meal photo')) {
      return 'Add a photo of your meal.';
    }

    if (validationMessage.includes('10 MB')) {
      return 'Meal photos must be 10 MB or smaller.';
    }

    if (validationMessage.includes('image')) {
      return INVALID_PHOTO_MESSAGE;
    }

    return null;
  }

  async function handleSubmit(event: SyntheticEvent<HTMLFormElement>) {
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
              ? 'border-[var(--color-primary)] bg-[linear-gradient(180deg,rgba(168,239,239,0.18),rgba(255,255,255,0.84))]'
              : 'border-[rgba(190,200,200,0.7)] bg-[linear-gradient(180deg,rgba(255,255,255,0.8),rgba(242,244,244,0.72))]'
          }`}
        >
          <div className='mb-3 flex h-14 w-14 items-center justify-center rounded-full border border-white/80 bg-white/92 shadow-[0_10px_30px_rgba(25,28,29,0.06)]'>
            <CameraUploadIcon />
          </div>
          <p className='text-sm font-semibold text-[var(--color-text)]'>
            Add a photo of your meal
          </p>
          <p className='mt-1 text-xs text-[var(--color-muted)]'>
            or choose from your gallery
          </p>
          <p className='mt-2 text-xs text-[var(--color-muted)]'>
            {SUPPORTED_MEAL_PHOTO_MESSAGE}
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
            accept={SUPPORTED_MEAL_PHOTO_ACCEPT}
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
