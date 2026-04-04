import { Link, useSearchParams } from 'react-router-dom';
import { SEEDED_MEMBERS } from '../types/member';
import { useEffect, useRef, useState } from 'react';

interface Props {
  currentMemberName: string;
  onMemberChange: () => void;
}

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();
}

export default function MemberSwitcher({
  currentMemberName,
  onMemberChange,
}: Props) {
  const [searchParams] = useSearchParams();
  const currentId = searchParams.get('memberId') ?? SEEDED_MEMBERS[0].id;
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      if (!menuRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setOpen(false);
      }
    }

    window.addEventListener('mousedown', handlePointerDown);
    window.addEventListener('keydown', handleEscape);

    return () => {
      window.removeEventListener('mousedown', handlePointerDown);
      window.removeEventListener('keydown', handleEscape);
    };
  }, []);

  function selectMember() {
    setOpen(false);
    onMemberChange();
  }

  function toggleMenu() {
    setOpen((current) => !current);
  }

  const currentMember =
    SEEDED_MEMBERS.find((member) => member.id === currentId) ??
    SEEDED_MEMBERS[0];
  const avatarLabel = currentMemberName || currentMember.name;
  const avatarInitials = getInitials(avatarLabel);

  return (
    <div ref={menuRef} className='relative z-30'>
      <button
        type='button'
        aria-haspopup='menu'
        aria-expanded={open}
        aria-label='Open account menu'
        onClick={toggleMenu}
        className='flex items-center gap-3 rounded-full border border-white/70 bg-white/85 px-2 py-2 pr-4 shadow-[0_10px_30px_rgba(25,28,29,0.08)] transition hover:border-[var(--color-primary)] hover:bg-white'
      >
        <span className='flex h-11 w-11 items-center justify-center rounded-full bg-[linear-gradient(135deg,var(--color-primary),var(--color-primary-strong))] text-sm font-bold text-white'>
          {avatarInitials}
        </span>
        <span className='hidden min-w-0 text-left sm:block'>
          <span className='block max-w-40 truncate text-sm font-semibold text-[var(--color-primary)]'>
            {avatarLabel}
          </span>
          <span className='block text-xs text-[var(--color-muted)]'>
            Account
          </span>
        </span>
        <span aria-hidden='true' className='text-sm text-[var(--color-muted)]'>
          ▾
        </span>
      </button>

      {open && (
        <div
          role='menu'
          aria-label='Account menu'
          className='absolute right-0 top-full z-[100] mt-3 w-[min(18rem,calc(100vw-2rem))] overflow-hidden rounded-[1.5rem] border border-white/80 bg-[rgba(255,255,255,0.98)] p-2 shadow-[0_32px_90px_rgba(11,33,33,0.2)] backdrop-blur-xl'
        >
          <div className='rounded-[1.25rem] bg-[rgba(168,239,239,0.18)] px-4 py-3'>
            <p className='text-xs font-semibold uppercase tracking-[0.16em] text-[var(--color-muted)]'>
              Switch account
            </p>
            <p className='mt-1 font-headline text-lg font-bold tracking-[-0.03em] text-[var(--color-primary)]'>
              {avatarLabel}
            </p>
          </div>

          <div className='mt-2 space-y-1'>
            {SEEDED_MEMBERS.map((member) => {
              const isCurrent = currentId === member.id;
              const search = `?memberId=${member.id}`;

              return (
                <Link
                  key={member.id}
                  to={{ search }}
                  role='menuitem'
                  onClick={selectMember}
                  aria-current={isCurrent ? 'page' : undefined}
                  className={`flex items-center justify-between rounded-[1rem] px-4 py-3 text-sm transition ${
                    isCurrent
                      ? 'bg-[var(--color-primary)] text-white'
                      : 'text-[var(--color-primary)] hover:bg-[rgba(168,239,239,0.18)]'
                  }`}
                >
                  <span className='font-semibold'>{member.name}</span>
                </Link>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
