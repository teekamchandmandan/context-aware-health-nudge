import type { MoodValue } from '../../types/member';
import { ApiError } from '../../api/client';

export interface FormProps {
  memberId: string;
  submitting: boolean;
  setSubmitting: (value: boolean) => void;
  onSuccess: (message: string) => void;
  onError: (message: string) => void;
  clearFeedback: () => void;
}

export type MealField = 'description' | 'photo';
export type MealFieldErrors = Partial<Record<MealField, string>>;

export type WeightUnit = 'lb' | 'kg';
export type WaterUnit = 'ml' | 'glasses';

export const MOOD_OPTIONS: Array<{ value: MoodValue; label: string }> = [
  { value: 'low', label: 'Low' },
  { value: 'neutral', label: 'Neutral' },
  { value: 'high', label: 'High' },
];

export const INPUT_CLASSES =
  'w-full rounded-[1rem] border border-[rgba(190,200,200,0.9)] bg-white px-4 py-3 text-sm text-[var(--color-text)] shadow-[inset_0_1px_2px_rgba(25,28,29,0.03)] transition focus:border-[var(--color-primary-strong)] focus:outline-none focus:ring-4 focus:ring-[rgba(168,239,239,0.45)]';

export const PRIMARY_BUTTON_CLASSES =
  'inline-flex items-center justify-center rounded-[1rem] bg-[var(--color-primary)] px-5 py-3 text-sm font-semibold text-white shadow-[0_16px_36px_rgba(0,66,66,0.18)] transition hover:-translate-y-0.5 hover:bg-[var(--color-primary-strong)] disabled:cursor-not-allowed disabled:opacity-60';

export const KG_TO_LB = 2.20462;
export const ML_PER_GLASS = 250;

export function parsePositiveNumber(value: string): number | null {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return null;
  }

  return parsed;
}

export function getValidationMessage(error: ApiError): string | null {
  if (typeof error.body === 'object' && error.body && 'detail' in error.body) {
    const detail = error.body.detail;

    if (typeof detail === 'string') {
      return detail;
    }

    if (Array.isArray(detail)) {
      const first = detail[0];
      if (first && typeof first === 'object' && 'msg' in first) {
        const message = first.msg;
        return typeof message === 'string' ? message : null;
      }
    }
  }

  return null;
}

export function getRequestErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 404) {
      console.error('Signal endpoint returned 404', error.body);
    }

    if (error.status === 0 || error.status === 404 || error.status >= 500) {
      return 'We could not save that. Please try again.';
    }
  }

  return 'We could not save that. Please try again.';
}
