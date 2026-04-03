import type { CoachEscalationItem } from '../types/member';

interface Props {
  items: CoachEscalationItem[];
}

const SOURCE_LABELS: Record<string, string> = {
  member_action: 'Member requested help',
  low_confidence: 'Low confidence',
  rule_engine: 'Rule engine',
};

function sourceLabel(source: string | null): string {
  return (source && SOURCE_LABELS[source]) ?? source ?? 'Unknown';
}

function formatTimestamp(ts: string): string {
  const d = new Date(ts);
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function CoachEscalationsList({ items }: Props) {
  if (items.length === 0) {
    return (
      <div className='bg-white rounded-xl border border-gray-200 p-6 text-center'>
        <p className='text-gray-500'>No open escalations right now.</p>
      </div>
    );
  }

  return (
    <ul className='space-y-3'>
      {items.map((esc) => (
        <li
          key={esc.escalation_id}
          className='bg-white rounded-xl border border-amber-200 p-4 space-y-2'
        >
          <div className='flex items-start justify-between gap-2'>
            <p className='text-sm font-semibold text-gray-900'>
              {esc.member_name}
            </p>
            <span
              className={`inline-flex items-center text-xs font-medium px-2 py-0.5 rounded-full ${
                esc.source === 'member_action'
                  ? 'bg-amber-100 text-amber-800'
                  : 'bg-red-100 text-red-800'
              }`}
            >
              {sourceLabel(esc.source)}
            </span>
          </div>
          {esc.reason && <p className='text-sm text-gray-700'>{esc.reason}</p>}
          <p className='text-xs text-gray-400'>
            {formatTimestamp(esc.created_at)}
          </p>
        </li>
      ))}
    </ul>
  );
}
