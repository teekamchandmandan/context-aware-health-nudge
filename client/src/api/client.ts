import type {
  MemberNudgeResponse,
  ActionResponse,
  SignalResponse,
  ActionType,
  SignalType,
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
  if (init?.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers,
    });
  } catch (error) {
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

export function fetchNudge(memberId: string): Promise<MemberNudgeResponse> {
  return request<MemberNudgeResponse>(
    `/api/members/${encodeURIComponent(memberId)}/nudge`,
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

export function resetSeed(): Promise<{ status: string }> {
  return request<{ status: string }>('/debug/reset-seed', { method: 'POST' });
}

export { ApiError };
