import type { CoachNudgeItem } from '../types/member';
import { formatTimestamp } from '../utils/formatTimestamp';

interface Props {
  items: CoachNudgeItem[];
}

function confidenceBand(c: number | null): {
  label: string;
  className: string;
} {
  if (c === null)
    return {
      label: '—',
      className: 'bg-[var(--color-surface-soft)] text-[var(--color-muted)]',
    };
  if (c >= 0.75)
    return {
      label: `${(c * 100).toFixed(0)}% confidence`,
      className: 'bg-[rgba(143,246,208,0.22)] text-[var(--color-accent)]',
    };
  if (c >= 0.5)
    return {
      label: `${(c * 100).toFixed(0)}% confidence`,
      className: 'bg-[rgba(255,209,102,0.25)] text-[var(--color-warning-text)]',
    };
  return {
    label: `${(c * 100).toFixed(0)}% confidence`,
    className: 'bg-[rgba(186,26,26,0.08)] text-[var(--color-error)]',
  };
}

const ACTION_LABELS: Record<string, string> = {
  act_now: 'Acted on it',
  dismiss: 'Dismissed',
  ask_for_help: 'Asked for help',
};

const STATUS_LABELS: Record<string, string> = {
  active: 'Active',
  acted: 'Acted',
  dismissed: 'Dismissed',
  escalated: 'Escalated',
  superseded: 'Superseded',
};

const STATUS_STYLES: Record<string, string> = {
  active: 'bg-[rgba(168,239,239,0.36)] text-[var(--color-primary)]',
  acted: 'bg-[rgba(143,246,208,0.22)] text-[var(--color-accent)]',
  dismissed: 'bg-[var(--color-surface-soft)] text-[var(--color-muted)]',
  escalated: 'bg-[rgba(255,209,102,0.25)] text-[var(--color-warning-text)]',
  superseded: 'bg-[var(--color-surface-soft)] text-[var(--color-muted)]',
};

const NUDGE_TYPE_LABELS: Record<string, string> = {
  meal_guidance: 'Meal guidance',
  weight_check_in: 'Weight check-in',
  support_risk: 'Support risk',
};

function nudgeTypeLabel(type: string): string {
  return NUDGE_TYPE_LABELS[type] ?? type.replace(/_/g, ' ');
}

export default function CoachNudgesList({ items }: Props) {
  if (items.length === 0) {
    return (
      <div className='rounded-[1.75rem] border border-white/80 bg-[rgba(255,255,255,0.82)] p-8 text-center shadow-[0_16px_48px_rgba(25,28,29,0.05)] backdrop-blur-xl'>
        <p className='font-headline text-lg font-bold tracking-[-0.03em] text-[var(--color-primary)]'>
          No nudges yet
        </p>
        <p className='mt-2 text-sm text-[var(--color-muted)]'>
          Nudges will appear here once members check in.
        </p>
      </div>
    );
  }

  return (
    <ul className='space-y-3'>
      {items.map((n) => {
        const band = confidenceBand(n.confidence);
        return (
          <li
            key={n.nudge_id}
            className='rounded-[1.75rem] border border-white/80 bg-[rgba(255,255,255,0.82)] p-5 shadow-[0_16px_48px_rgba(25,28,29,0.05)] backdrop-blur-xl'
          >
            <div className='flex items-start justify-between gap-3'>
              <div className='min-w-0'>
                <p className='font-headline text-base font-bold tracking-[-0.03em] text-[var(--color-primary)]'>
                  {n.member_name}
                </p>
                <p className='text-xs text-[var(--color-muted)]'>
                  {nudgeTypeLabel(n.nudge_type)}
                </p>
              </div>
              <span
                className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold ${
                  STATUS_STYLES[n.status] ??
                  'bg-[var(--color-surface-soft)] text-[var(--color-muted)]'
                }`}
              >
                {STATUS_LABELS[n.status] ?? n.status}
              </span>
            </div>

            {n.content && (
              <p className='mt-3 text-sm leading-relaxed text-[var(--color-text)]'>
                {n.content}
              </p>
            )}

            <div className='mt-3 flex flex-wrap items-center gap-2 text-xs'>
              <span
                className={`rounded-full px-3 py-1 font-medium ${band.className}`}
              >
                {band.label}
              </span>
              {n.escalation_recommended && (
                <span className='rounded-full bg-[rgba(255,209,102,0.25)] px-3 py-1 font-medium text-[var(--color-warning-text)]'>
                  Escalation recommended
                </span>
              )}
              {n.matched_reason && (
                <span className='rounded-full bg-[var(--color-surface-soft)] px-3 py-1 text-[var(--color-muted)]'>
                  {n.matched_reason}
                </span>
              )}
            </div>

            <div className='mt-3 flex items-center justify-between text-xs text-[var(--color-muted)]'>
              <span>
                {n.latest_action
                  ? (ACTION_LABELS[n.latest_action] ?? n.latest_action)
                  : 'No action yet'}
              </span>
              <span>{formatTimestamp(n.created_at)}</span>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
