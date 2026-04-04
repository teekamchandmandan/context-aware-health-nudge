import { useState } from 'react';

export function useCardFeedback(onSuccess: (message: string) => void) {
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  function clearFeedback() {
    setApiError(null);
  }

  function handleSuccess(message: string) {
    onSuccess(message);
  }

  return {
    submitting,
    setSubmitting,
    apiError,
    setApiError,
    clearFeedback,
    handleSuccess,
  };
}
