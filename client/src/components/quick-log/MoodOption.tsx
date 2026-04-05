import type { MoodValue } from '../../types/member';
import { MOOD_OPTIONS } from './shared';

type MoodIconPalette = {
  stroke: string;
  halo: string;
  face: string;
  accent: string;
};

const DEFAULT_MOOD_PALETTE: MoodIconPalette = {
  stroke: 'var(--color-primary)',
  halo: 'rgba(186,235,245,0.55)',
  face: 'rgba(255,255,255,0.96)',
  accent: 'var(--color-primary-strong)',
};

const SELECTED_MOOD_PALETTE: MoodIconPalette = {
  stroke: '#ffffff',
  halo: 'rgba(255,255,255,0.18)',
  face: 'rgba(255,255,255,0.08)',
  accent: 'rgba(255,255,255,0.92)',
};

const MOOD_ICON_PROPS = {
  width: 24,
  height: 24,
  viewBox: '0 0 28 28',
  fill: 'none',
  'aria-hidden': true,
} as const;

const MOOD_ICON_STROKE_PROPS = {
  strokeWidth: 1.8,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
};

function renderMoodGlyph(mood: MoodValue, palette: MoodIconPalette) {
  const strokeProps = {
    ...MOOD_ICON_STROKE_PROPS,
    stroke: palette.stroke,
  };

  switch (mood) {
    case 'low':
      return (
        <>
          <path d='M10.25 11.9l1.55-.9' {...strokeProps} />
          <path d='M17.75 11.9l-1.55-.9' {...strokeProps} />
          <path
            d='M10.6 18.15c1.1-1.7 2.24-2.55 3.4-2.55 1.16 0 2.3.85 3.4 2.55'
            {...strokeProps}
          />
        </>
      );
    case 'neutral':
      return (
        <>
          <circle cx='11.15' cy='12.25' r='1.05' fill={palette.stroke} />
          <circle cx='16.85' cy='12.25' r='1.05' fill={palette.stroke} />
          <path d='M10.8 17.2h6.4' {...strokeProps} />
        </>
      );
    case 'high':
      return (
        <>
          <circle cx='11.15' cy='12.05' r='1.05' fill={palette.stroke} />
          <circle cx='16.85' cy='12.05' r='1.05' fill={palette.stroke} />
          <path
            d='M10.1 16.2c1 1.65 2.3 2.5 3.9 2.5 1.58 0 2.9-.85 3.9-2.5'
            {...strokeProps}
          />
          <path
            d='M20.4 8.8c.34 1.12 1.02 1.8 2.05 2.05-1.03.28-1.71.96-2.05 2.05-.28-1.09-.95-1.77-2-2.05 1.05-.25 1.72-.93 2-2.05Z'
            fill={palette.accent}
          />
        </>
      );
  }
}

function MoodIcon({ mood, selected }: { mood: MoodValue; selected: boolean }) {
  const palette = selected ? SELECTED_MOOD_PALETTE : DEFAULT_MOOD_PALETTE;

  return (
    <svg {...MOOD_ICON_PROPS}>
      <circle cx='14' cy='14' r='10.5' fill={palette.halo} />
      <circle
        cx='14'
        cy='14'
        r='7.75'
        fill={palette.face}
        stroke={palette.stroke}
        strokeWidth='1.8'
      />
      {renderMoodGlyph(mood, palette)}
    </svg>
  );
}

export default function MoodOption({
  option,
  groupName,
  selected,
  disabled,
  errorId,
  onSelect,
}: {
  option: (typeof MOOD_OPTIONS)[number];
  groupName: string;
  selected: boolean;
  disabled: boolean;
  errorId?: string;
  onSelect: (mood: MoodValue) => void;
}) {
  const iconContainerClassName = selected
    ? 'border-transparent bg-[linear-gradient(180deg,var(--color-primary),var(--color-primary-strong))] shadow-[0_12px_28px_rgba(0,66,66,0.24)]'
    : 'border-white/80 bg-white shadow-[0_10px_28px_rgba(25,28,29,0.06)] hover:border-[rgba(0,66,66,0.14)] hover:bg-[rgba(255,255,255,0.96)]';
  const labelClassName = selected
    ? 'text-[var(--color-primary)]'
    : 'text-[var(--color-muted)]';

  return (
    <label className='cursor-pointer text-center transition'>
      <input
        type='radio'
        name={groupName}
        value={option.value}
        checked={selected}
        onChange={() => onSelect(option.value)}
        disabled={disabled}
        aria-invalid={errorId ? true : undefined}
        aria-describedby={errorId}
        className='sr-only'
      />
      <span className='flex flex-col items-center gap-1.5'>
        <span
          className={`flex h-12 w-12 items-center justify-center rounded-full border transition ${iconContainerClassName}`}
        >
          <MoodIcon mood={option.value} selected={selected} />
        </span>
        <span className={`text-xs font-semibold ${labelClassName}`}>
          {option.label}
        </span>
      </span>
    </label>
  );
}
