import type { CoachNudgeItem } from '../types/member';
import { formatTimestamp } from '../utils/formatTimestamp';

interface Props {
  items: CoachNudgeItem[];
}

function confidenceBand(c: number | null): {
  label: string;
  className: string;
} {
  if (c === null) return { label: '—', className: 'bg-gray-100 text-gray-600' };
  if (c >= 0.75)
    return { label: 'High', className: 'bg-green-100 text-green-800' };
  if (c >= 0.5)
    return { label: 'Medium', className: 'bg-yellow-100 text-yellow-800' };
  return { label: 'Low', className: 'bg-red-100 text-red-800' };
}

const ACTION_LABELS: Record<string, string> = {
  act_now: 'Acted',
  dismiss: 'Dismissed',
  ask_for_help: 'Asked for help',
};

const STATUS_STYLES: Record<string, string> = {
  active: 'bg-blue-100 text-blue-800',
  acted: 'bg-green-100 text-green-800',
  dismissed: 'bg-gray-100 text-gray-600',
  escalated: 'bg-amber-100 text-amber-800',
  superseded: 'bg-gray-100 text-gray-500',
};

export default function CoachNudgesList({ items }: Props) {
  if (items.length === 0) {
    return (
      <div className='bg-white rounded-xl border border-gray-200 p-6 text-center'>
        <p className='text-gray-500'>No recent nudges yet.</p>
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
            className='bg-white rounded-xl border border-gray-200 p-4 space-y-2'
          >
            {/* Row 1: member + status */}
            <div className='flex items-start justify-between gap-2'>
              <div className='min-w-0'>
                <p className='text-sm font-semibold text-gray-900'>
                  {n.member_name}
                </p>
                <p className='text-xs text-gray-500 capitalize'>
                  {n.nudge_type.replace(/_/g, ' ')}
                </p>
              </div>
              <span
                className={`inline-flex items-center text-xs font-medium px-2 py-0.5 rounded-full whitespace-nowrap ${
                  STATUS_STYLES[n.status] ?? 'bg-gray-100 text-gray-600'
                }`}
              >
                {n.status}
              </span>
            </div>

            {/* Row 2: content */}
            {n.content && (
              <p className='text-sm text-gray-800 leading-relaxed'>
                {n.content}
              </p>
            )}

            {/* Row 3: explanation */}
            {n.explanation && (
              <p className='text-xs text-gray-500 leading-relaxed'>
                {n.explanation}
              </p>
            )}

            {/* Row 4: metadata chips */}
            <div className='flex flex-wrap items-center gap-2 text-xs'>
              {n.matched_reason && (
                <span className='bg-gray-100 text-gray-700 px-2 py-0.5 rounded'>
                  {n.matched_reason}
                </span>
              )}
              <span className={`px-2 py-0.5 rounded ${band.className}`}>
                {n.confidence !== null
                  ? `${(n.confidence * 100).toFixed(0)}% ${band.label}`
                  : band.label}
              </span>
              {n.escalation_recommended && (
                <span className='bg-amber-100 text-amber-800 px-2 py-0.5 rounded'>
                  Escalation rec.
                </span>
              )}
              <span className='bg-gray-50 text-gray-500 px-2 py-0.5 rounded'>
                {n.phrasing_source}
              </span>
            </div>

            {/* Row 5: latest action + timestamp */}
            <div className='flex items-center justify-between text-xs text-gray-400'>
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
