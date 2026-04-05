import type {
  MemberNudgeResponse,
  ActionResponse,
  SignalResponse,
  ActionType,
  SignalType,
  CoachNudgeListResponse,
  CoachEscalationListResponse,
  CoachEscalationItem,
  LatestSignalsResponse,
} from '../types/member';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

type ApiErrorBody = string | { detail?: unknown } | null;

class ApiError extends Error {
  status: number;
  body: ApiErrorBody;

  constructor(status: number, message: string, body: ApiErrorBody = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

function parseErrorMessage(body: ApiErrorBody): string {
  if (typeof body === 'string' && body.length > 0) {
    return body;
  }

  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = body.detail;
    if (typeof detail === 'string' && detail.length > 0) {
      return detail;
    }
  }

  return 'Request failed';
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;

  const headers = new Headers(init?.headers);
  if (
    init?.body &&
    !(init.body instanceof FormData) &&
    !headers.has('Content-Type')
  ) {
    headers.set('Content-Type', 'application/json');
  }

  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers,
    });
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw error;
    throw new ApiError(
      0,
      error instanceof Error ? error.message : 'Network request failed',
    );
  }

  if (!res.ok) {
    let body: ApiErrorBody = null;

    try {
      body = (await res.json()) as ApiErrorBody;
    } catch {
      try {
        body = await res.text();
      } catch {
        body = null;
      }
    }

    throw new ApiError(res.status, parseErrorMessage(body), body);
  }

  return res.json() as Promise<T>;
}

export function fetchNudge(
  memberId: string,
  signal?: AbortSignal,
): Promise<MemberNudgeResponse> {
  return request<MemberNudgeResponse>(
    `/api/members/${encodeURIComponent(memberId)}/nudge`,
    { signal },
  );
}

export function fetchLatestSignals(
  memberId: string,
  signal?: AbortSignal,
): Promise<LatestSignalsResponse> {
  return request<LatestSignalsResponse>(
    `/api/members/${encodeURIComponent(memberId)}/signals/latest`,
    { signal },
  );
}

export function postAction(
  nudgeId: string,
  actionType: ActionType,
): Promise<ActionResponse> {
  return request<ActionResponse>(
    `/api/nudges/${encodeURIComponent(nudgeId)}/action`,
    {
      method: 'POST',
      body: JSON.stringify({ action_type: actionType }),
    },
  );
}

export function postSignal(
  memberId: string,
  signalType: SignalType,
  payload: Record<string, unknown>,
): Promise<SignalResponse> {
  return request<SignalResponse>(
    `/api/members/${encodeURIComponent(memberId)}/signals`,
    {
      method: 'POST',
      body: JSON.stringify({ signal_type: signalType, payload }),
    },
  );
}

export function postMealLog(
  memberId: string,
  formData: FormData,
): Promise<SignalResponse> {
  return request<SignalResponse>(
    `/api/members/${encodeURIComponent(memberId)}/meal-logs`,
    {
      method: 'POST',
      body: formData,
    },
  );
}

export function resetSeed(): Promise<{ status: string }> {
  return request<{ status: string }>('/debug/reset-seed', { method: 'POST' });
}

export function fetchCoachNudges(limit = 20): Promise<CoachNudgeListResponse> {
  return request<CoachNudgeListResponse>(`/api/coach/nudges?limit=${limit}`);
}

export function fetchCoachEscalations(
  limit = 20,
): Promise<CoachEscalationListResponse> {
  return request<CoachEscalationListResponse>(
    `/api/coach/escalations?limit=${limit}`,
  );
}

export function resolveEscalation(
  escalationId: string,
): Promise<CoachEscalationItem> {
  return request<CoachEscalationItem>(
    `/api/coach/escalations/${encodeURIComponent(escalationId)}/resolve`,
    { method: 'POST' },
  );
}

export { ApiError };
