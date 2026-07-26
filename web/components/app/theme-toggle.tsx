'use client';

import { useTheme } from 'next-themes';
import { MonitorIcon, MoonIcon, SunIcon } from '@phosphor-icons/react';
import { cn } from '@/lib/shadcn/utils';

interface ThemeToggleProps {
  className?: string;
}

export function ThemeToggle({ className }: ThemeToggleProps) {
  const { theme, setTheme } = useTheme();
  const nextTheme = theme === 'dark' ? 'light' : theme === 'light' ? 'system' : 'dark';
  const ThemeIcon = theme === 'dark' ? MoonIcon : theme === 'light' ? SunIcon : MonitorIcon;

  return (
    <button
      type="button"
      onClick={() => setTheme(nextTheme)}
      aria-label="Change color scheme"
      title="Change color scheme"
      className={cn(
        'border-disha-leaf/15 bg-disha-paper/70 text-disha-leaf/45 hover:border-disha-leaf/25 hover:text-disha-leaf/70 focus-visible:ring-disha-sun shadow-disha-ink/5 grid size-11 cursor-pointer place-items-center rounded-full border opacity-60 shadow-sm transition-[color,border-color,opacity] duration-200 hover:opacity-100 focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none',
        className
      )}
      style={{ transform: 'translate(calc(50vw - 3.75rem), -4rem)' }}
    >
      <ThemeIcon suppressHydrationWarning size={16} weight="bold" aria-hidden="true" />
    </button>
  );
}
