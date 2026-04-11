import { useState } from 'react';
import type { CoachEscalationItem } from '../types/member';
import { formatTimestamp } from '../utils/formatTimestamp';

interface Props {
  items: CoachEscalationItem[];
  onResolve: (escalationId: string) => Promise<void>;
}

const SOURCE_LABELS: Record<string, string> = {
  member_action: 'Member asked for help',
  low_confidence: 'Low confidence',
  rule_engine: 'Rule engine',
};

const SOURCE_ICONS: Record<string, string> = {
  member_action: '🙋',
  low_confidence: '⚠',
  rule_engine: '⚙',
};

function sourceLabel(source: string | null): string {
  return (source && SOURCE_LABELS[source]) ?? source ?? 'Unknown';
}

function sourceIcon(source: string | null): string {
  return (source && SOURCE_ICONS[source]) ?? '•';
}

function ResolveButton({
  escalationId,
  onResolve,
}: {
  escalationId: string;
  onResolve: (id: string) => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);

  async function handleClick() {
    setBusy(true);
    try {
      await onResolve(escalationId);
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      type='button'
      disabled={busy}
      onClick={handleClick}
      className='rounded-full border border-[var(--color-accent)] bg-[rgba(143,246,208,0.15)] px-3 py-1 text-xs font-semibold text-[var(--color-primary)] transition hover:bg-[rgba(143,246,208,0.35)] disabled:opacity-50'
    >
      {busy ? 'Resolving…' : 'Resolve'}
    </button>
  );
}

export default function CoachEscalationsList({ items, onResolve }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);

  if (items.length === 0) {
    return (
      <div className='rounded-[1.75rem] border border-white/80 bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(242,244,244,0.95))] p-8 text-center shadow-[0_16px_48px_rgba(25,28,29,0.05)] backdrop-blur-xl'>
        <div className='mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[rgba(143,246,208,0.22)]'>
          <svg
            className='h-6 w-6 text-[var(--color-accent)]'
            fill='none'
            viewBox='0 0 24 24'
            strokeWidth={2}
            stroke='currentColor'
          >
            <path
              strokeLinecap='round'
              strokeLinejoin='round'
              d='M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z'
            />
          </svg>
        </div>
        <p className='font-headline text-lg font-bold tracking-[-0.03em] text-[var(--color-primary)]'>
          No open escalations
        </p>
        <p className='mt-2 text-sm text-[var(--color-muted)]'>
          All members are on track right now.
        </p>
      </div>
    );
  }

  return (
    <ul className='space-y-3'>
      {items.map((esc) => {
        const isMemberRequest = esc.source === 'member_action';
        const isExpanded = expanded === esc.escalation_id;

        return (
          <li
            key={esc.escalation_id}
            className={`overflow-hidden rounded-[1.75rem] border shadow-[0_16px_48px_rgba(25,28,29,0.05)] backdrop-blur-xl transition hover:shadow-[0_20px_60px_rgba(25,28,29,0.09)] ${
              isMemberRequest
                ? 'border-[#f2dba8] bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(255,241,214,0.9))]'
                : 'border-white/80 bg-[rgba(255,255,255,0.82)]'
            }`}
          >
            <button
              type='button'
              onClick={() => setExpanded(isExpanded ? null : esc.escalation_id)}
              aria-expanded={isExpanded}
              className='flex w-full items-center gap-4 p-5 text-left'
            >
              <div className='min-w-0 flex-1'>
                <div className='flex items-center gap-2'>
                  <span className='text-lg leading-none' aria-hidden='true'>
                    {sourceIcon(esc.source)}
                  </span>
                  <p className='font-headline text-base font-bold tracking-[-0.03em] text-[var(--color-primary)]'>
                    {esc.member_name}
                  </p>
                  <span className='text-xs text-[var(--color-muted)]'>·</span>
                  <span className='text-xs text-[var(--color-muted)]'>
                    {formatTimestamp(esc.created_at)}
                  </span>
                </div>
                {esc.reason && (
                  <p className='mt-1 line-clamp-1 text-sm text-[var(--color-text)]'>
                    {esc.reason}
                  </p>
                )}
              </div>

              <div className='flex shrink-0 items-center gap-2'>
                <span
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${
                    isMemberRequest
                      ? 'bg-[rgba(255,209,102,0.3)] text-[var(--color-warning-text)]'
                      : 'bg-[rgba(186,26,26,0.1)] text-[var(--color-error)]'
                  }`}
                >
                  {sourceLabel(esc.source)}
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
                <div className='space-y-4'>
                  {esc.reason && (
                    <section className='rounded-[1.35rem] border border-[rgba(168,239,239,0.4)] bg-[linear-gradient(135deg,rgba(168,239,239,0.16),rgba(255,255,255,0.92))] p-4 sm:p-5'>
                      <p className='text-xs font-semibold uppercase tracking-[0.14em] text-[var(--color-primary)]'>
                        Reason
                      </p>
                      <p className='mt-3 text-pretty font-headline text-lg font-semibold leading-8 text-[var(--color-primary)] sm:text-[1.35rem]'>
                        {esc.reason}
                      </p>
                    </section>
                  )}

                  <section className='rounded-[1.35rem] border border-[rgba(190,200,200,0.45)] bg-white/72 p-4'>
                    <p className='text-xs font-semibold uppercase tracking-[0.14em] text-[var(--color-muted)]'>
                      Context
                    </p>
                    <div className='mt-3 flex flex-wrap items-center gap-2'>
                      <span
                        className={`rounded-full px-3 py-1 text-xs font-medium ${
                          isMemberRequest
                            ? 'bg-[rgba(255,209,102,0.25)] text-[var(--color-warning-text)]'
                            : 'bg-[var(--color-surface-soft)] text-[var(--color-muted)]'
                        }`}
                      >
                        {sourceLabel(esc.source)}
                      </span>
                      <span className='rounded-full bg-[var(--color-surface-soft)] px-3 py-1 text-xs text-[var(--color-muted)]'>
                        {esc.member_name}
                      </span>
                      <span className='rounded-full bg-[rgba(168,239,239,0.2)] px-3 py-1 text-xs text-[var(--color-primary)]'>
                        Open
                      </span>
                    </div>
                  </section>
                </div>

                <div className='mt-4 flex items-center justify-between border-t border-[rgba(190,200,200,0.25)] pt-3'>
                  <span className='text-xs text-[var(--color-muted)]'>
                    Escalated {formatTimestamp(esc.created_at)}
                  </span>
                  <ResolveButton
                    escalationId={esc.escalation_id}
                    onResolve={onResolve}
                  />
                </div>
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
