import type { CoachEscalationItem } from '../types/member';
import { formatTimestamp } from '../utils/formatTimestamp';

interface Props {
  items: CoachEscalationItem[];
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

export default function CoachEscalationsList({ items }: Props) {
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
    <ul className='grid gap-4 sm:grid-cols-2 lg:grid-cols-3'>
      {items.map((esc) => {
        const isMemberRequest = esc.source === 'member_action';
        return (
          <li
            key={esc.escalation_id}
            className={`rounded-[1.75rem] border p-5 shadow-[0_16px_48px_rgba(25,28,29,0.05)] backdrop-blur-xl transition hover:shadow-[0_20px_60px_rgba(25,28,29,0.09)] ${
              isMemberRequest
                ? 'border-[#f2dba8] bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(255,241,214,0.9))]'
                : 'border-white/80 bg-[rgba(255,255,255,0.82)]'
            }`}
          >
            <div className='flex items-start justify-between gap-2'>
              <div className='flex items-center gap-2'>
                <span className='text-lg leading-none' aria-hidden='true'>
                  {sourceIcon(esc.source)}
                </span>
                <p className='font-headline text-base font-bold tracking-[-0.03em] text-[var(--color-primary)]'>
                  {esc.member_name}
                </p>
              </div>
              <span
                className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold ${
                  isMemberRequest
                    ? 'bg-[rgba(255,209,102,0.3)] text-[var(--color-warning-text)]'
                    : 'bg-[rgba(186,26,26,0.1)] text-[var(--color-error)]'
                }`}
              >
                {sourceLabel(esc.source)}
              </span>
            </div>
            {esc.reason && (
              <p className='mt-3 text-sm leading-relaxed text-[var(--color-text)]'>
                {esc.reason}
              </p>
            )}
            <div className='mt-4 flex items-center justify-between border-t border-[rgba(190,200,200,0.35)] pt-3'>
              <p className='text-xs text-[var(--color-muted)]'>
                Escalated {formatTimestamp(esc.created_at)}
              </p>
              <span className='text-xs font-medium capitalize text-[var(--color-primary)]'>
                {esc.status}
              </span>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
