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

export type MealField = 'photo';
export type MealFieldErrors = Partial<Record<MealField, string>>;

export type WeightUnit = 'lb' | 'kg';

export const MOOD_OPTIONS: Array<{
  value: MoodValue;
  label: string;
}> = [
  { value: 'low', label: 'Low' },
  { value: 'neutral', label: 'Okay' },
  { value: 'high', label: 'Great' },
];

export const MOOD_LABELS: Record<MoodValue, string> = Object.fromEntries(
  MOOD_OPTIONS.map(({ value, label }) => [value, label]),
) as Record<MoodValue, string>;

export const INPUT_CLASSES =
  'w-full rounded-[1rem] border border-[rgba(190,200,200,0.9)] bg-white px-4 py-3 text-sm text-[var(--color-text)] shadow-[inset_0_1px_2px_rgba(25,28,29,0.03)] transition focus:border-[var(--color-primary-strong)] focus:outline-none focus:ring-4 focus:ring-[rgba(168,239,239,0.45)]';

export const SELECT_CLASSES =
  'shrink-0 appearance-none rounded-[1rem] border border-[rgba(190,200,200,0.9)] bg-white bg-[url("data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%2714%27 height=%279%27 viewBox=%270 0 14 9%27 fill=%27none%27%3E%3Cpath d=%27M1.25 1.5L7 7l5.75-5.5%27 stroke=%27%23004242%27 stroke-width=%271.75%27 stroke-linecap=%27round%27 stroke-linejoin=%27round%27/%3E%3C/svg%3E")] bg-[length:14px_9px] bg-[right_12px_center] bg-no-repeat py-3 pl-3 pr-8 text-sm font-semibold text-[var(--color-text)] shadow-[inset_0_1px_2px_rgba(25,28,29,0.03)] transition focus:border-[var(--color-primary-strong)] focus:outline-none focus:ring-4 focus:ring-[rgba(168,239,239,0.45)]';

export const PRIMARY_BUTTON_CLASSES =
  'inline-flex items-center justify-center rounded-[1rem] bg-[var(--color-primary)] px-5 py-3 text-sm font-semibold text-white shadow-[0_16px_36px_rgba(0,66,66,0.18)] transition hover:-translate-y-0.5 hover:bg-[var(--color-primary-strong)] disabled:cursor-not-allowed disabled:opacity-60';

export const KG_TO_LB = 2.20462;
export const ML_PER_GLASS = 250;
export const REQUEST_ERROR_MESSAGE =
  'We could not save that. Please try again.';

export function parsePositiveNumber(
  value: string,
  maximum?: number,
): number | null {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return null;
  }

  if (typeof maximum === 'number' && parsed > maximum) {
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
  if (error instanceof ApiError && error.status === 404) {
    console.error('Request endpoint returned 404', error.body);
  }

  return REQUEST_ERROR_MESSAGE;
}
