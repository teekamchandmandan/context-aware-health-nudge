import { useState } from 'react';
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
      label: `${(c * 100).toFixed(0)}%`,
      className: 'bg-[rgba(143,246,208,0.22)] text-[var(--color-accent)]',
    };
  if (c >= 0.5)
    return {
      label: `${(c * 100).toFixed(0)}%`,
      className: 'bg-[rgba(255,209,102,0.25)] text-[var(--color-warning-text)]',
    };
  return {
    label: `${(c * 100).toFixed(0)}%`,
    className: 'bg-[rgba(186,26,26,0.08)] text-[var(--color-error)]',
  };
}

const ACTION_LABELS: Record<string, { text: string; icon: string }> = {
  act_now: { text: 'Acted on it', icon: '✓' },
  dismiss: { text: 'Dismissed', icon: '✕' },
  ask_for_help: { text: 'Asked for help', icon: '?' },
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

const PHRASING_LABELS: Record<string, string> = {
  template: 'Template',
  llm: 'LLM-refined',
};

function nudgeTypeLabel(type: string): string {
  return NUDGE_TYPE_LABELS[type] ?? type.replace(/_/g, ' ');
}

export default function CoachNudgesList({ items }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);

  if (items.length === 0) {
    return (
      <div className='rounded-[1.75rem] border border-white/80 bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(242,244,244,0.95))] p-8 text-center shadow-[0_16px_48px_rgba(25,28,29,0.05)] backdrop-blur-xl'>
        <div className='mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[rgba(168,239,239,0.2)]'>
          <svg
            className='h-6 w-6 text-[var(--color-primary)]'
            fill='none'
            viewBox='0 0 24 24'
            strokeWidth={2}
            stroke='currentColor'
          >
            <path
              strokeLinecap='round'
              strokeLinejoin='round'
              d='M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0'
            />
          </svg>
        </div>
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
        const isExpanded = expanded === n.nudge_id;
        const actionInfo = n.latest_action
          ? ACTION_LABELS[n.latest_action]
          : null;

        return (
          <li
            key={n.nudge_id}
            className='overflow-hidden rounded-[1.75rem] border border-white/80 bg-[rgba(255,255,255,0.82)] shadow-[0_16px_48px_rgba(25,28,29,0.05)] backdrop-blur-xl transition hover:shadow-[0_20px_60px_rgba(25,28,29,0.09)]'
          >
            <button
              type='button'
              onClick={() => setExpanded(isExpanded ? null : n.nudge_id)}
              aria-expanded={isExpanded}
              className='flex w-full items-center gap-4 p-5 text-left'
            >
              <div className='min-w-0 flex-1'>
                <div className='flex items-center gap-2'>
                  <p className='font-headline text-base font-bold tracking-[-0.03em] text-[var(--color-primary)]'>
                    {n.member_name}
                  </p>
                  <span className='text-xs text-[var(--color-muted)]'>·</span>
                  <span className='text-xs text-[var(--color-muted)]'>
                    {nudgeTypeLabel(n.nudge_type)}
                  </span>
                </div>
                {n.content && (
                  <p className='mt-1 line-clamp-1 text-sm text-[var(--color-text)]'>
                    {n.content}
                  </p>
                )}
              </div>

              <div className='flex shrink-0 items-center gap-2'>
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${band.className}`}
                >
                  {band.label}
                </span>
                <span
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${
                    STATUS_STYLES[n.status] ??
                    'bg-[var(--color-surface-soft)] text-[var(--color-muted)]'
                  }`}
                >
                  {STATUS_LABELS[n.status] ?? n.status}
                </span>
                <svg
                  className={`h-4 w-4 text-[var(--color-muted)] transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                  fill='none'
                  viewBox='0 0 24 24'
                  strokeWidth={2}
                  stroke='currentColor'
                >
                  <path
                    strokeLinecap='round'
                    strokeLinejoin='round'
                    d='m19.5 8.25-7.5 7.5-7.5-7.5'
                  />
                </svg>
              </div>
            </button>

            {isExpanded && (
              <div className='border-t border-[rgba(190,200,200,0.35)] bg-[linear-gradient(180deg,rgba(249,251,251,0.82),rgba(255,255,255,0.94))] px-5 py-5'>
                <div
                  className={`grid gap-4 ${
                    n.content
                      ? 'lg:grid-cols-[minmax(0,1.35fr)_minmax(17rem,1fr)]'
                      : 'lg:grid-cols-1'
                  }`}
                >
                  {n.content && (
                    <section className='rounded-[1.35rem] border border-[rgba(168,239,239,0.4)] bg-[linear-gradient(135deg,rgba(168,239,239,0.16),rgba(255,255,255,0.92))] p-4 sm:p-5'>
                      <p className='text-xs font-semibold uppercase tracking-[0.14em] text-[var(--color-primary)]'>
                        Suggested nudge
                      </p>
                      <p className='mt-3 text-pretty font-headline text-lg font-semibold leading-8 text-[var(--color-primary)] sm:text-[1.35rem]'>
                        {n.content}
                      </p>
                    </section>
                  )}

                  <div className='space-y-4'>
                    {n.explanation && (
                      <section className='rounded-[1.35rem] border border-[rgba(190,200,200,0.45)] bg-white/80 p-4 sm:p-5'>
                        <p className='text-xs font-semibold uppercase tracking-[0.14em] text-[var(--color-muted)]'>
                          Why it matched
                        </p>
                        <p className='mt-3 text-sm leading-7 text-[var(--color-text)] sm:text-[0.95rem]'>
                          {n.explanation}
                        </p>
                      </section>
                    )}

                    <section className='rounded-[1.35rem] border border-[rgba(190,200,200,0.45)] bg-white/72 p-4'>
                      <p className='text-xs font-semibold uppercase tracking-[0.14em] text-[var(--color-muted)]'>
                        Context
                      </p>
                      {n.visible_food_summary && (
                        <p className='mt-3 text-sm leading-7 text-[var(--color-text)] sm:text-[0.95rem]'>
                          {n.visible_food_summary}
                        </p>
                      )}
                      <div className='mt-3 flex flex-wrap items-center gap-2'>
                        {n.escalation_recommended && (
                          <span className='rounded-full bg-[rgba(255,209,102,0.25)] px-3 py-1 text-xs font-medium text-[var(--color-warning-text)]'>
                            Escalation recommended
                          </span>
                        )}
                        {n.matched_reason && (
                          <span className='rounded-full bg-[var(--color-surface-soft)] px-3 py-1 text-xs text-[var(--color-muted)]'>
                            {n.matched_reason}
                          </span>
                        )}
                        <span className='rounded-full bg-[var(--color-surface-soft)] px-3 py-1 text-xs text-[var(--color-muted)]'>
                          {PHRASING_LABELS[n.phrasing_source] ??
                            n.phrasing_source}
                        </span>
                      </div>
                    </section>
                  </div>
                </div>

                <div className='mt-4 flex items-center justify-between border-t border-[rgba(190,200,200,0.25)] pt-3 text-xs text-[var(--color-muted)]'>
                  <span>
                    {actionInfo ? (
                      <span className='inline-flex items-center gap-1 font-medium'>
                        <span className='font-medium'>{actionInfo.icon}</span>
                        {actionInfo.text}
                      </span>
                    ) : (
                      'No member action yet'
                    )}
                  </span>
                  <span>{formatTimestamp(n.created_at)}</span>
                </div>
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
