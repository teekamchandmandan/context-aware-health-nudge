// Enums
export type NudgeState = 'active' | 'no_nudge' | 'escalated';
export type ActionType = 'act_now' | 'dismiss' | 'ask_for_help';
export type SignalType = 'weight_logged' | 'mood_logged' | 'sleep_logged';
export type MealType = 'breakfast' | 'lunch' | 'dinner' | 'snack';
export type MoodValue = 'low' | 'neutral' | 'high';

// Latest signals — typed payloads per signal kind
export interface WeightSignalEntry {
  payload: { weight_lb: number };
  logged_at: string;
}
export interface SleepSignalEntry {
  payload: { sleep_hours: number };
  logged_at: string;
}
export interface MoodSignalEntry {
  payload: { mood: MoodValue };
  logged_at: string;
}

export interface LatestSignalsResponse {
  weight_logged?: WeightSignalEntry;
  sleep_logged?: SleepSignalEntry;
  mood_logged?: MoodSignalEntry;
}

// Responses
export interface MemberRef {
  id: string;
  name: string;
}

export interface NudgeDetail {
  id: string;
  nudge_type: string;
  content: string | null;
  explanation: string | null;
  matched_reason: string | null;
  confidence: number | null;
  escalation_recommended: boolean;
  status: string;
  phrasing_source: string;
  created_at: string;
}

export interface MemberNudgeResponse {
  state: NudgeState;
  member: MemberRef;
  nudge?: NudgeDetail | null;
}

export interface ActionResponse {
  nudge_id: string;
  action_type: string;
  nudge_status: string;
  recorded_at: string;
}

export interface SignalResponse {
  id: string;
  member_id: string;
  signal_type: string;
  payload: Record<string, unknown>;
  created_at: string;
}

// Request shapes
export interface ActionRequest {
  action_type: ActionType;
}

export interface SignalRequest {
  signal_type: SignalType;
  payload: Record<string, unknown>;
}

// Coach responses
export interface CoachNudgeItem {
  nudge_id: string;
  member_id: string;
  member_name: string;
  nudge_type: string;
  visible_food_summary: string | null;
  content: string | null;
  explanation: string | null;
  matched_reason: string | null;
  confidence: number | null;
  escalation_recommended: boolean;
  status: string;
  latest_action: string | null;
  phrasing_source: string;
  created_at: string;
}

export interface CoachNudgeListResponse {
  items: CoachNudgeItem[];
  limit: number;
  count: number;
}

export interface CoachEscalationItem {
  escalation_id: string;
  member_id: string;
  member_name: string;
  reason: string | null;
  source: string | null;
  status: string;
  created_at: string;
}

export interface CoachEscalationListResponse {
  items: CoachEscalationItem[];
  limit: number;
  count: number;
}

// Seeded member metadata for the switcher
export interface SeededMember {
  id: string;
  name: string;
  scenario: string;
}

export const SEEDED_MEMBERS: SeededMember[] = [
  { id: 'member_meal_01', name: 'Alice Chen', scenario: 'Meal mismatch' },
  {
    id: 'member_weight_01',
    name: 'Bob Martinez',
    scenario: 'Missing check-in',
  },
  {
    id: 'member_support_01',
    name: 'Carol Davis',
    scenario: 'Support escalation',
  },
  {
    id: 'member_catchup_01',
    name: 'Diego Rivera',
    scenario: 'All caught up',
  },
];
