import { useState } from 'react';
import Link from 'next/link';
import { LoaderCircle, Mic } from 'lucide-react';
import { DishaBrand } from '@/components/disha/disha-brand';
import { useDishaCopy } from '@/lib/disha-copy';
import { DISHA_PICKER_LANGUAGES, type DishaLanguage } from '@/lib/disha-language';
import { cn } from '@/lib/shadcn/utils';

interface WelcomeViewProps {
  language: DishaLanguage;
  onLanguageChange: (language: DishaLanguage) => void;
  onStartCall: () => Promise<void>;
}

export const WelcomeView = ({
  language,
  onLanguageChange,
  onStartCall,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  const [isStarting, setIsStarting] = useState(false);
  const { welcome } = useDishaCopy();

  const handleStartCall = async () => {
    if (isStarting) return;

    setIsStarting(true);
    try {
      await onStartCall();
    } finally {
      setIsStarting(false);
    }
  };

  return (
    <div ref={ref} className="bg-disha-wash relative isolate min-h-svh overflow-x-hidden">
      <style>{`
        @keyframes disha-mic-shine-sweep {
          0% {
            transform: translateY(-115%);
          }
          54%,
          100% {
            transform: translateY(160%);
          }
        }

        .disha-mic-shine {
          animation: disha-mic-shine-sweep 8.2s cubic-bezier(0.45, 0, 0.55, 1) infinite;
          transform: translateY(-115%);
          will-change: transform;
        }

        @media (prefers-reduced-motion: reduce) {
          .disha-mic-shine {
            animation: none;
            transform: translateY(-28%);
            will-change: auto;
          }
        }
      `}</style>

      <header className="absolute inset-x-0 top-0 z-20 flex items-center justify-between px-4 py-3 sm:px-6 sm:py-5">
        <DishaBrand showTagline={false} />
        <Link
          href="/counsellor"
          className="text-disha-leaf hover:text-disha-ink focus-visible:ring-disha-sun focus-visible:ring-offset-disha-wash dark:hover:text-disha-sun min-h-11 touch-manipulation rounded-full px-3 py-3 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
        >
          {welcome.counsellorView}
        </Link>
      </header>

      <main className="relative z-10 mx-auto flex min-h-svh w-full max-w-4xl items-center justify-center px-4 pt-20 pb-6 sm:px-7 sm:pt-24 sm:pb-8">
        <section className="flex w-full translate-y-3 flex-col items-center text-center sm:translate-y-4">
          <h1 className="text-disha-ink dark:text-disha-leaf max-w-md text-[1.75rem] leading-[1.3] font-semibold text-balance sm:text-3xl md:text-[2.5rem] md:leading-[1.2]">
            {welcome.heading}
          </h1>

          <div className="relative mt-[clamp(0.875rem,2.5svh,1.25rem)] grid size-[clamp(13rem,30svh,15rem)] place-items-center md:mt-6 md:size-[18rem]">
            <span
              className="pointer-events-none absolute -inset-20 rounded-full md:-inset-24 dark:hidden"
              style={{
                backgroundImage:
                  'radial-gradient(circle, color-mix(in srgb, var(--disha-sun) 22%, transparent) 0%, color-mix(in srgb, var(--disha-sun) 12%, transparent) 50%, transparent 80%)',
              }}
              aria-hidden="true"
            />
            <span
              className="pointer-events-none absolute -inset-20 hidden rounded-full md:-inset-24 dark:block"
              style={{
                backgroundImage:
                  'radial-gradient(circle, color-mix(in srgb, var(--disha-sun) 16%, transparent) 0%, color-mix(in srgb, var(--disha-sun) 8%, transparent) 50%, transparent 76%)',
              }}
              aria-hidden="true"
            />

            <button
              type="button"
              disabled={isStarting}
              aria-busy={isStarting}
              aria-describedby="voice-action"
              aria-label={isStarting ? welcome.micStartingAriaLabel : welcome.micAriaLabel}
              onClick={() => void handleStartCall()}
              className="bg-disha-leaf text-disha-paper focus-visible:ring-disha-sun focus-visible:ring-offset-disha-wash dark:bg-disha-leaf dark:text-disha-ink ring-disha-paper/20 dark:ring-disha-sun/25 relative z-10 grid size-[clamp(11rem,25svh,13rem)] touch-manipulation place-items-center overflow-hidden rounded-full px-5 text-center ring-1 transition-[transform,opacity] duration-200 hover:scale-[1.02] focus-visible:ring-4 focus-visible:ring-offset-4 focus-visible:outline-none active:scale-[0.98] disabled:cursor-wait disabled:opacity-75 md:size-60"
              style={{
                boxShadow:
                  '0 2px 3px color-mix(in srgb, var(--disha-ink) 36%, transparent), 0 18px 38px -16px color-mix(in srgb, var(--disha-ink) 72%, transparent), inset 0 1px 0 color-mix(in srgb, var(--disha-sun) 26%, transparent)',
              }}
            >
              {!isStarting && (
                <>
                  <span
                    className="disha-mic-shine pointer-events-none absolute inset-x-[-8%] top-0 h-[72%] dark:hidden"
                    style={{
                      backgroundImage:
                        'linear-gradient(to bottom, transparent 0%, color-mix(in srgb, var(--disha-paper) 4%, transparent) 18%, color-mix(in srgb, var(--disha-paper) 13%, transparent) 40%, color-mix(in srgb, var(--disha-paper) 19%, transparent) 52%, color-mix(in srgb, var(--disha-paper) 10%, transparent) 66%, color-mix(in srgb, var(--disha-paper) 3%, transparent) 84%, transparent 100%)',
                    }}
                    aria-hidden="true"
                  />
                  <span
                    className="disha-mic-shine pointer-events-none absolute inset-x-[-8%] top-0 hidden h-[72%] dark:block"
                    style={{
                      backgroundImage:
                        'linear-gradient(to bottom, transparent 0%, color-mix(in srgb, var(--disha-sun) 2%, transparent) 18%, color-mix(in srgb, var(--disha-sun) 6%, transparent) 40%, color-mix(in srgb, var(--disha-sun) 9%, transparent) 52%, color-mix(in srgb, var(--disha-sun) 5%, transparent) 66%, color-mix(in srgb, var(--disha-sun) 2%, transparent) 84%, transparent 100%)',
                    }}
                    aria-hidden="true"
                  />
                </>
              )}

              <span className="relative z-10 flex -translate-y-1 flex-col items-center">
                {isStarting ? (
                  <LoaderCircle
                    className="size-12 animate-spin motion-reduce:animate-none md:size-16"
                    aria-hidden="true"
                  />
                ) : (
                  <span className="bg-disha-sun text-disha-ink grid size-14 place-items-center rounded-full md:size-[4.5rem]">
                    <Mic className="size-7 md:size-9" strokeWidth={2.4} aria-hidden="true" />
                  </span>
                )}
                <span className="mt-2 max-w-36 text-base leading-[1.45] font-semibold text-balance md:mt-3 md:max-w-44 md:text-xl">
                  {isStarting ? welcome.micStartingLabel : welcome.micLabel}
                </span>
              </span>
            </button>
          </div>

          <p aria-live="polite" className="sr-only">
            {isStarting ? welcome.loadingStatus : ''}
          </p>

          <p
            id="voice-action"
            className="text-disha-ink dark:text-disha-leaf mt-[clamp(0.875rem,2.5svh,1.25rem)] max-w-md px-2 text-sm leading-6 font-medium text-pretty"
          >
            {welcome.voiceAction}
          </p>

          <fieldset className="mt-1 max-w-full">
            <legend className="sr-only">{welcome.languagePickerLegend}</legend>
            <div className="flex flex-wrap items-center justify-center gap-x-1">
              {DISHA_PICKER_LANGUAGES.map((option) => {
                const isSelected = option.value === language;
                return (
                  <button
                    key={option.value}
                    type="button"
                    aria-pressed={isSelected}
                    onClick={() => onLanguageChange(option.value)}
                    className={cn(
                      'focus-visible:ring-disha-sun focus-visible:ring-offset-disha-wash relative min-h-11 touch-manipulation rounded-lg px-2.5 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none',
                      isSelected
                        ? 'text-disha-ink dark:text-disha-sun after:bg-disha-sun after:absolute after:inset-x-2.5 after:bottom-1 after:h-0.5 after:rounded-full'
                        : 'text-disha-leaf hover:text-disha-ink dark:hover:text-disha-sun'
                    )}
                  >
                    {welcome.languageOptions[option.value]}
                  </button>
                );
              })}
            </div>
          </fieldset>
        </section>
      </main>
    </div>
  );
};
