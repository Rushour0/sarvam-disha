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
  const streams = Object.values(welcome.streams);

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
      <header className="absolute inset-x-0 top-0 z-20 flex items-center justify-between px-4 py-3 sm:px-6 sm:py-5">
        <DishaBrand showTagline={false} />
        <Link
          href="/counsellor"
          className="text-disha-leaf/70 hover:text-disha-leaf focus-visible:ring-disha-sun min-h-11 touch-manipulation rounded-full px-3 py-3 text-xs font-medium transition-colors focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
        >
          {welcome.counsellorView}
        </Link>
      </header>

      <main className="relative z-10 mx-auto flex min-h-svh w-full max-w-4xl justify-center px-4 pt-[clamp(4.25rem,10svh,5.5rem)] pb-8 sm:px-7 md:items-center md:py-24">
        <div
          className="pointer-events-none absolute inset-0 z-0 overflow-hidden"
          aria-hidden="true"
        >
          <span
            className="pointer-events-none absolute top-[clamp(15rem,33svh,17rem)] left-1/2 h-[clamp(52rem,145svh,76rem)] w-[clamp(46rem,180vw,80rem)] -translate-x-1/2 -translate-y-1/2 md:top-[55%] dark:opacity-45"
            style={{
              backgroundImage:
                'radial-gradient(ellipse at center, color-mix(in srgb, var(--disha-sun) 5%, transparent) 0%, color-mix(in srgb, var(--disha-sun) 4%, transparent) 24%, color-mix(in srgb, var(--disha-sun) 2%, transparent) 54%, transparent 84%)',
            }}
            aria-hidden="true"
          />
          <span
            className="pointer-events-none absolute top-[clamp(15rem,33svh,17rem)] left-1/2 h-[clamp(42rem,112svh,58rem)] w-[clamp(34rem,140vw,62rem)] -translate-x-1/2 -translate-y-1/2 md:top-[55%] dark:opacity-50"
            style={{
              backgroundImage:
                'radial-gradient(ellipse at center, color-mix(in srgb, var(--disha-sun) 8%, transparent) 0%, color-mix(in srgb, var(--disha-sun) 6%, transparent) 28%, color-mix(in srgb, var(--disha-sun) 3%, transparent) 58%, transparent 86%)',
            }}
            aria-hidden="true"
          />
          <span
            className="pointer-events-none absolute top-[clamp(15rem,33svh,17rem)] left-1/2 h-[clamp(30rem,82svh,42rem)] w-[clamp(26rem,105vw,44rem)] -translate-x-1/2 -translate-y-1/2 md:top-[55%] dark:opacity-60"
            style={{
              backgroundImage:
                'radial-gradient(ellipse at center, color-mix(in srgb, var(--disha-sun) 12%, transparent) 0%, color-mix(in srgb, var(--disha-sun) 9%, transparent) 30%, color-mix(in srgb, var(--disha-sun) 4%, transparent) 62%, transparent 88%)',
            }}
            aria-hidden="true"
          />
        </div>

        <section className="relative z-10 flex w-full flex-col items-center text-center">
          <div className="text-disha-leaf flex items-center justify-center gap-2">
            <span className="bg-disha-leaf/30 h-px w-5" aria-hidden="true" />
            <p className="text-xs leading-5 font-semibold uppercase">{welcome.eyebrow}</p>
            <span className="bg-disha-sun size-1.5 rounded-full" aria-hidden="true" />
          </div>

          <h1 className="text-disha-ink dark:text-disha-leaf mt-1 max-w-xl text-[1.75rem] leading-[1.3] font-semibold text-balance sm:mt-2 sm:text-3xl md:text-[2.5rem] md:leading-[1.2]">
            {welcome.heading}
          </h1>

          <div className="relative mt-[clamp(0.75rem,2svh,1.25rem)] grid size-52 place-items-center md:mt-6 md:size-[18rem]">
            <span
              className="pointer-events-none absolute -inset-8 rounded-full opacity-55 motion-safe:animate-[pulse_7.2s_cubic-bezier(0.45,0,0.55,1)_infinite] motion-reduce:animate-none md:-inset-10 dark:opacity-30"
              style={{
                backgroundImage:
                  'radial-gradient(circle, transparent 54%, color-mix(in srgb, var(--disha-sun) 7%, transparent) 64%, color-mix(in srgb, var(--disha-sun) 4%, transparent) 72%, transparent 84%)',
              }}
              aria-hidden="true"
            />
            <span
              className="pointer-events-none absolute -inset-3 rounded-full opacity-65 motion-safe:animate-[pulse_7.2s_cubic-bezier(0.45,0,0.55,1)_infinite] motion-safe:[animation-delay:-2.4s] motion-reduce:animate-none md:-inset-4 dark:opacity-35"
              style={{
                backgroundImage:
                  'radial-gradient(circle, transparent 56%, color-mix(in srgb, var(--disha-sun) 10%, transparent) 66%, color-mix(in srgb, var(--disha-sun) 5%, transparent) 75%, transparent 86%)',
              }}
              aria-hidden="true"
            />
            <span
              className="pointer-events-none absolute inset-1 rounded-full opacity-75 motion-safe:animate-[pulse_7.2s_cubic-bezier(0.45,0,0.55,1)_infinite] motion-safe:[animation-delay:-4.8s] motion-reduce:animate-none md:inset-3 dark:opacity-40"
              style={{
                backgroundImage:
                  'radial-gradient(circle, transparent 58%, color-mix(in srgb, var(--disha-sun) 13%, transparent) 68%, color-mix(in srgb, var(--disha-sun) 6%, transparent) 77%, transparent 88%)',
              }}
              aria-hidden="true"
            />

            <button
              type="button"
              disabled={isStarting}
              aria-busy={isStarting}
              aria-describedby="voice-action voice-outcome voice-meta"
              aria-label={isStarting ? welcome.micStartingAriaLabel : welcome.micAriaLabel}
              onClick={() => void handleStartCall()}
              className="bg-disha-leaf text-disha-paper focus-visible:ring-disha-sun focus-visible:ring-offset-disha-wash dark:bg-disha-ink dark:text-disha-leaf relative z-10 grid size-44 touch-manipulation place-items-center rounded-full px-5 text-center transition-[transform,opacity] duration-200 [--mic-depth:var(--disha-ink)] hover:scale-[1.02] focus-visible:ring-4 focus-visible:ring-offset-4 focus-visible:outline-none active:scale-[0.98] disabled:cursor-wait disabled:opacity-75 md:size-60 dark:[--mic-depth:var(--disha-wash)]"
              style={{
                boxShadow:
                  '0 2px 3px color-mix(in srgb, var(--mic-depth) 44%, transparent), 0 14px 24px -12px color-mix(in srgb, var(--mic-depth) 60%, transparent), 0 34px 64px -24px color-mix(in srgb, var(--mic-depth) 50%, transparent), inset 0 2px 1px color-mix(in srgb, var(--disha-paper) 34%, transparent), inset 0 -20px 26px -20px color-mix(in srgb, var(--mic-depth) 88%, transparent)',
              }}
            >
              <span className="flex -translate-y-1 flex-col items-center">
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
                <span className="mt-2 max-w-36 text-base leading-[1.45] font-semibold text-balance md:mt-3 md:max-w-40 md:text-xl">
                  {isStarting ? welcome.micStartingLabel : welcome.micLabel}
                </span>
              </span>
            </button>
          </div>

          <p aria-live="polite" className="sr-only">
            {isStarting ? welcome.loadingStatus : ''}
          </p>

          <div className="mt-[clamp(0.75rem,2svh,1.25rem)] max-w-xl px-2">
            <p
              id="voice-action"
              className="text-disha-ink/85 dark:text-disha-leaf/90 text-[0.8125rem] leading-5 font-medium text-pretty"
            >
              {welcome.voiceAction}
            </p>
            <p
              id="voice-outcome"
              className="text-disha-ink/65 dark:text-disha-leaf/75 mt-1 text-[0.8125rem] leading-5 text-pretty"
            >
              {welcome.voiceOutcome}
            </p>
            <p id="voice-meta" className="text-disha-leaf/65 mt-1 text-xs leading-5 font-medium">
              {welcome.voiceMeta}
            </p>
          </div>

          <div className="mt-1 flex w-full max-w-3xl flex-col items-center">
            <fieldset className="max-w-full">
              <legend className="sr-only">{welcome.languagePickerLegend}</legend>
              <div className="flex flex-wrap items-center justify-center gap-x-0.5">
                <span className="text-disha-leaf/65 mr-1 text-xs" aria-hidden="true">
                  {welcome.languagePickerLabel}
                </span>
                {DISHA_PICKER_LANGUAGES.map((option) => {
                  const isSelected = option.value === language;
                  return (
                    <button
                      key={option.value}
                      type="button"
                      aria-pressed={isSelected}
                      onClick={() => onLanguageChange(option.value)}
                      className={cn(
                        'focus-visible:ring-disha-sun relative min-h-11 touch-manipulation rounded-lg px-2 text-xs font-medium transition-colors focus-visible:ring-2 focus-visible:ring-offset-1 focus-visible:outline-none',
                        isSelected
                          ? 'text-disha-ink dark:text-disha-sun after:bg-disha-sun after:absolute after:inset-x-2 after:bottom-1.5 after:h-0.5 after:rounded-full'
                          : 'text-disha-leaf/65 hover:text-disha-leaf'
                      )}
                    >
                      {welcome.languageOptions[option.value]}
                    </button>
                  );
                })}
              </div>
            </fieldset>

            <div
              className="border-disha-leaf/10 mt-6 w-full max-w-2xl border-t pt-4"
              aria-label={welcome.proofLabel}
            >
              <p className="text-disha-ink/45 dark:text-disha-leaf/55 text-xs leading-5 text-pretty">
                {welcome.trustLine}
              </p>
              <p className="text-disha-leaf/55 mt-1.5 text-xs leading-5 font-semibold">
                {welcome.proofLabel}
              </p>
              <ul className="text-disha-leaf/45 mt-1 flex flex-wrap justify-center gap-x-1.5 gap-y-0.5 text-xs leading-5">
                {streams.map((stream) => (
                  <li key={stream} className="after:ml-1.5 after:content-['·'] last:after:hidden">
                    {stream}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
};
