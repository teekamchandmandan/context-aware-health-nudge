import { useState } from 'react';

export function useCardFeedback(onSignalSubmitted: () => void) {
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  function clearFeedback() {
    setSuccess(null);
    setApiError(null);
  }

  function handleSuccess(message: string) {
    setSuccess(message);
    onSignalSubmitted();
  }

  return {
    submitting,
    setSubmitting,
    success,
    apiError,
    setApiError,
    clearFeedback,
    handleSuccess,
  };
}
