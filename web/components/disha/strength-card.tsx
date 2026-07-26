'use client';

import { useEffect, useRef, useState } from 'react';
import { CheckCircle2, Sparkles } from 'lucide-react';
import { SignupCard } from '@/components/disha/signup-card';
import { Button } from '@/components/ui/button';
import type { DishaStrength } from '@/lib/disha-events';

interface StrengthCardProps {
  strengths: DishaStrength[];
}

export function StrengthCard({ strengths }: StrengthCardProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const continueButtonRef = useRef<HTMLButtonElement>(null);
  const previouslyFocusedRef = useRef<HTMLElement | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const [showSignup, setShowSignup] = useState(false);
  const [signedUp, setSignedUp] = useState(false);

  useEffect(() => {
    if (dismissed || strengths.length === 0) return;

    previouslyFocusedRef.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    continueButtonRef.current?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setDismissed(true);
        return;
      }

      if (event.key !== 'Tab') return;
      const focusable = dialogRef.current?.querySelectorAll<HTMLElement>(
        'button:not([disabled]), input:not([disabled]), [href], [tabindex]:not([tabindex="-1"])'
      );
      if (!focusable || focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      previouslyFocusedRef.current?.focus();
    };
  }, [dismissed, strengths.length]);

  if (dismissed || strengths.length === 0) return null;

  return (
    <div className="bg-disha-wash/80 motion-safe:animate-in motion-safe:fade-in fixed inset-x-3 top-20 bottom-32 z-40 grid place-items-center overflow-y-auto px-2 py-3 backdrop-blur-sm motion-safe:duration-200 md:inset-x-6 md:top-24 md:bottom-36">
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="strength-reveal-title"
        aria-describedby="strength-reveal-description"
        className="border-disha-sun/40 bg-card motion-safe:animate-in motion-safe:slide-in-from-bottom-2 max-h-full w-full max-w-xl overflow-y-auto rounded-[1.75rem] border p-5 shadow-[0_20px_60px_-40px_rgba(22,74,71,0.45)] motion-safe:duration-200 sm:p-6"
      >
        <div className="bg-disha-sun/12 text-disha-leaf grid size-11 place-items-center rounded-full">
          <Sparkles className="size-5" aria-hidden="true" />
        </div>
        <h2
          id="strength-reveal-title"
          className="mt-4 text-2xl leading-tight font-semibold tracking-tight"
        >
          आपकी ताकत
        </h2>
        <p
          id="strength-reveal-description"
          className="text-muted-foreground mt-2 text-sm leading-6"
        >
          आपकी अपनी बातों में ये खूबियाँ साफ़ सुनाई दीं।
        </p>

        <ul className="mt-5 space-y-3">
          {strengths.map((strength) => (
            <li
              key={strength.label}
              className="border-border/70 bg-disha-paper rounded-[1.5rem] border p-4"
            >
              <p className="text-disha-leaf leading-6 font-semibold">{strength.label}</p>
              <blockquote className="text-muted-foreground mt-2 text-sm leading-6">
                “{strength.evidence_quote}”
              </blockquote>
            </li>
          ))}
        </ul>

        {signedUp ? (
          <div
            role="status"
            aria-live="polite"
            className="border-disha-leaf/35 bg-disha-leaf/10 mt-5 rounded-[1.5rem] border p-4"
          >
            <CheckCircle2 className="text-disha-leaf size-6" aria-hidden="true" />
            <p className="mt-2 font-semibold">आपका टेस्ट अब शुरू हो रहा है</p>
            <p className="text-muted-foreground mt-1 text-sm leading-6">
              Disha अब आवाज़ में पाँच सवाल पूछेगी। बस वैसे ही जवाब दें जैसे बातचीत कर रहे हैं।
            </p>
          </div>
        ) : (
          showSignup && (
            <div className="mt-5">
              <SignupCard prominent onSignedUp={() => setSignedUp(true)} />
            </div>
          )
        )}

        <div className="mt-5 grid gap-2 sm:grid-cols-2">
          <Button
            ref={continueButtonRef}
            type="button"
            variant="outline"
            onClick={() => setDismissed(true)}
            className="focus-visible:ring-ring min-h-11 rounded-full focus-visible:ring-2"
          >
            बात जारी रखें
          </Button>
          {!showSignup && !signedUp && (
            <Button
              type="button"
              onClick={() => setShowSignup(true)}
              className="focus-visible:ring-ring min-h-11 rounded-full focus-visible:ring-2"
            >
              टेस्ट लें
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
