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

function sourceLabel(source: string | null): string {
  return (source && SOURCE_LABELS[source]) ?? source ?? 'Unknown';
}

export default function CoachEscalationsList({ items }: Props) {
  if (items.length === 0) {
    return (
      <div className='rounded-[1.75rem] border border-white/80 bg-[rgba(255,255,255,0.82)] p-8 text-center shadow-[0_16px_48px_rgba(25,28,29,0.05)] backdrop-blur-xl'>
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
            className={`rounded-[1.75rem] border p-5 shadow-[0_16px_48px_rgba(25,28,29,0.05)] backdrop-blur-xl ${
              isMemberRequest
                ? 'border-[#f2dba8] bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(255,241,214,0.9))]'
                : 'border-white/80 bg-[rgba(255,255,255,0.82)]'
            }`}
          >
            <div className='flex items-start justify-between gap-2'>
              <p className='font-headline text-base font-bold tracking-[-0.03em] text-[var(--color-primary)]'>
                {esc.member_name}
              </p>
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
              <p className='mt-3 text-sm leading-relaxed text-[var(--color-muted)]'>
                {esc.reason}
              </p>
            )}
            <p className='mt-3 text-xs text-[var(--color-muted)]'>
              Escalated {formatTimestamp(esc.created_at)}
            </p>
          </li>
        );
      })}
    </ul>
  );
}
