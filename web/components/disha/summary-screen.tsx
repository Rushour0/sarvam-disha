'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowRight, CheckCircle2, HeartHandshake, PhoneOff, RotateCcw } from 'lucide-react';
import { DishaBrand } from '@/components/disha/disha-brand';
import { useDishaSession } from '@/components/disha/disha-session-provider';
import { ExploreList } from '@/components/disha/explore-list';
import { PatternCard } from '@/components/disha/pattern-card';
import { SignupCard } from '@/components/disha/signup-card';
import { Button } from '@/components/ui/button';
import { useDishaCopy } from '@/lib/disha-copy';
import type { SummaryEvent } from '@/lib/disha-events';

interface SummaryScreenProps {
  summary: SummaryEvent;
  callDurationMs: number;
  isConnected: boolean;
  onEndCall: () => void;
  onNewSession: () => void;
}

const LONG_CALL_MS = 5 * 60 * 1000;

/** A student who already left a number on this device has nothing left to
 *  unlock, so never ask them twice for the same references. */
function hasExistingSignup(): boolean {
  try {
    const stored: unknown = JSON.parse(window.localStorage.getItem('disha.signups') ?? '[]');
    return Array.isArray(stored) && stored.length > 0;
  } catch {
    return false;
  }
}

export function SummaryScreen({
  summary,
  callDurationMs,
  isConnected,
  onEndCall,
  onNewSession,
}: SummaryScreenProps) {
  const { snapshot } = useDishaSession();
  const copy = useDishaCopy();
  const longCall = callDurationMs >= LONG_CALL_MS;
  const [unlocked, setUnlocked] = useState(false);

  useEffect(() => {
    if (hasExistingSignup()) setUnlocked(true);
  }, []);

  return (
    <section className="bg-disha-wash fixed inset-0 z-20 overflow-y-auto">
      <div className="mx-auto w-full max-w-5xl px-4 py-6 sm:px-6 md:py-10">
        <DishaBrand />

        <div className="mt-8 grid gap-4 md:mt-12 md:grid-cols-[1.45fr_0.8fr]">
          <article className="border-border/70 bg-card rounded-[2rem] border p-5 shadow-[0_24px_80px_-52px_rgba(22,74,71,0.6)] sm:p-8">
            <div className="bg-disha-leaf/10 text-disha-leaf mb-5 inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-semibold">
              <CheckCircle2 className="size-4" />
              {copy.summary.badge}
            </div>
            <h1 className="max-w-xl text-2xl leading-tight font-semibold tracking-tight text-balance sm:text-3xl">
              {copy.summary.heading}
            </h1>
            <p className="text-muted-foreground mt-4 text-base leading-7">{summary.summary_hi}</p>

            <div className="mt-8">
              <h2 className="text-sm font-semibold">{copy.summary.shortlist}</h2>
              {summary.shortlist.length > 0 ? (
                <ol className="mt-3 space-y-2">
                  {summary.shortlist.map((path, index) => (
                    <li
                      key={`${path}-${index}`}
                      className="border-border/70 bg-disha-paper flex gap-3 rounded-xl border p-3 text-sm leading-5"
                    >
                      <span className="bg-disha-sun text-disha-ink grid size-6 shrink-0 place-items-center rounded-full font-mono text-xs font-bold">
                        {index + 1}
                      </span>
                      {path}
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="text-muted-foreground mt-2 text-sm">{copy.summary.emptyShortlist}</p>
              )}
            </div>

            <div className="mt-8">
              <h2 className="text-sm font-semibold">{copy.summary.nextSteps}</h2>
              <ul className="mt-3 space-y-2.5">
                {summary.next_steps.map((step, index) => (
                  <li key={`${step}-${index}`} className="flex gap-3 text-sm leading-6">
                    <ArrowRight className="text-disha-leaf mt-1 size-4 shrink-0" />
                    {step}
                  </li>
                ))}
              </ul>
            </div>
          </article>

          <div className="space-y-4">
            <SignupCard prominent={longCall} onSignedUp={() => setUnlocked(true)} />
            <aside className="border-disha-sun/35 bg-disha-sun/10 rounded-[1.5rem] border p-5">
              <HeartHandshake className="text-disha-leaf size-6" />
              <h2 className="mt-4 font-semibold">{copy.summary.parentsTitle}</h2>
              <p className="text-muted-foreground mt-2 text-sm leading-6">
                {copy.summary.parentsBody}
              </p>
            </aside>

            <div className="border-border/70 bg-card rounded-[1.5rem] border p-4">
              {isConnected ? (
                <Button onClick={onEndCall} className="w-full rounded-full">
                  <PhoneOff />
                  {copy.summary.endCall}
                </Button>
              ) : (
                <Button onClick={onNewSession} className="w-full rounded-full">
                  <RotateCcw />
                  {copy.summary.newConversation}
                </Button>
              )}
              <Button asChild variant="ghost" className="mt-2 w-full rounded-full">
                <Link href="/me">मेरी प्रोफ़ाइल</Link>
              </Button>
              <Button asChild variant="ghost" className="mt-2 w-full rounded-full">
                <Link href="/explore">Career index</Link>
              </Button>
              <Button asChild variant="ghost" className="mt-2 w-full rounded-full">
                <Link href="/counsellor">{copy.summary.counsellorView}</Link>
              </Button>
            </div>
          </div>
        </div>

        <div className="mt-4 space-y-4">
          <PatternCard snapshot={snapshot} />
          <ExploreList
            snapshot={snapshot}
            unlocked={unlocked}
            gate={
              <SignupCard
                prominent
                title={copy.explore.lockedTitle}
                body={copy.explore.lockedBody}
                onSignedUp={() => setUnlocked(true)}
                footer={
                  <button
                    type="button"
                    onClick={() => setUnlocked(true)}
                    className="text-muted-foreground hover:text-foreground focus-visible:ring-ring mt-3 min-h-11 w-full rounded-full text-sm underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:outline-none"
                  >
                    {copy.explore.lockedSkip}
                  </button>
                }
              />
            }
          />
        </div>
      </div>
    </section>
  );
}
