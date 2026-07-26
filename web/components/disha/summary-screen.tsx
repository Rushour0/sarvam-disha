'use client';

import Link from 'next/link';
import {
  ArrowRight,
  Award,
  CheckCircle2,
  HeartHandshake,
  PhoneOff,
  RotateCcw,
  Sparkles,
} from 'lucide-react';
import { DishaBrand } from '@/components/disha/disha-brand';
import { useDishaSession } from '@/components/disha/disha-session-provider';
import { SignupCard } from '@/components/disha/signup-card';
import { Button } from '@/components/ui/button';
import type { SummaryEvent } from '@/lib/disha-events';

interface SummaryScreenProps {
  summary: SummaryEvent;
  callDurationMs: number;
  isConnected: boolean;
  onEndCall: () => void;
  onNewSession: () => void;
}

const LONG_CALL_MS = 5 * 60 * 1000;

export function SummaryScreen({
  summary,
  callDurationMs,
  isConnected,
  onEndCall,
  onNewSession,
}: SummaryScreenProps) {
  const { snapshot } = useDishaSession();
  const longCall = callDurationMs >= LONG_CALL_MS;
  return (
    <section className="bg-disha-wash fixed inset-0 z-20 overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl px-4 py-6 sm:px-6 md:py-10">
        <DishaBrand />

        <div className="mt-8 grid gap-4 md:mt-12 md:grid-cols-[1.45fr_0.8fr]">
          <article className="border-border/70 bg-card rounded-[2rem] border p-5 shadow-[0_24px_80px_-52px_rgba(22,74,71,0.6)] sm:p-8">
            <div className="bg-disha-leaf/10 text-disha-leaf mb-5 inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-semibold">
              <CheckCircle2 className="size-4" />
              बातचीत का सार
            </div>
            <h1 className="max-w-xl text-2xl leading-tight font-semibold tracking-tight text-balance sm:text-3xl">
              अब आगे की दिशा साफ़ है
            </h1>
            <p className="text-muted-foreground mt-4 text-base leading-7">{summary.summary_hi}</p>

            {snapshot.strengths.length > 0 && (
              <section aria-labelledby="summary-strengths-title" className="mt-8">
                <div className="flex items-center gap-2">
                  <Sparkles className="text-disha-sun size-4" aria-hidden="true" />
                  <h2 id="summary-strengths-title" className="text-sm font-semibold">
                    आपकी ताकत
                  </h2>
                </div>
                <ul className="mt-3 space-y-2">
                  {snapshot.strengths.map((strength) => (
                    <li
                      key={strength.label}
                      className="border-disha-sun/30 bg-disha-sun/10 rounded-[1.5rem] border p-4"
                    >
                      <p className="text-disha-leaf leading-6 font-semibold">{strength.label}</p>
                      <blockquote className="text-muted-foreground mt-1.5 text-sm leading-6">
                        “{strength.evidence_quote}”
                      </blockquote>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {snapshot.testResult && (
              <section
                aria-labelledby="summary-test-result-title"
                className="border-disha-leaf/30 bg-disha-leaf/10 mt-6 rounded-[1.5rem] border p-4"
              >
                <div className="flex items-center gap-2">
                  <Award className="text-disha-leaf size-4" aria-hidden="true" />
                  <h2 id="summary-test-result-title" className="text-sm font-semibold">
                    आपके टेस्ट का नतीजा
                  </h2>
                </div>
                <p className="text-disha-leaf mt-3 font-semibold">{snapshot.testResult.stream}</p>
                <p className="text-muted-foreground mt-1 text-sm leading-6">
                  {snapshot.testResult.fit_note}
                </p>
              </section>
            )}

            <div className="mt-8">
              <h2 className="text-sm font-semibold">आपकी shortlist</h2>
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
                <p className="text-muted-foreground mt-2 text-sm">
                  इस बातचीत में कोई verified path shortlist नहीं हुआ।
                </p>
              )}
            </div>

            <div className="mt-8">
              <h2 className="text-sm font-semibold">अगले कदम</h2>
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
            <SignupCard prominent={longCall} />
            <aside className="border-disha-sun/35 bg-disha-sun/10 rounded-[1.5rem] border p-5">
              <HeartHandshake className="text-disha-leaf size-6" />
              <h2 className="mt-4 font-semibold">माता-पिता के लिए</h2>
              <p className="text-muted-foreground mt-2 text-sm leading-6">
                परिवार के साथ साझा करने वाला सरल भाषा का सार अगले milestone में यहाँ आएगा।
              </p>
            </aside>

            <div className="border-border/70 bg-card rounded-[1.5rem] border p-4">
              {isConnected ? (
                <Button onClick={onEndCall} className="w-full rounded-full">
                  <PhoneOff />
                  बातचीत समाप्त करें
                </Button>
              ) : (
                <Button onClick={onNewSession} className="w-full rounded-full">
                  <RotateCcw />
                  नई बातचीत
                </Button>
              )}
              <Button asChild variant="ghost" className="mt-2 w-full rounded-full">
                <Link href="/counsellor">काउंसलर view देखें</Link>
              </Button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
