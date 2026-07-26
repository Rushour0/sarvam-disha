'use client';

import { Award, BookOpen, Check, GraduationCap, Leaf, Route, Sparkles } from 'lucide-react';
import { useDishaSession } from '@/components/disha/disha-session-provider';
import { StrengthCard } from '@/components/disha/strength-card';
import { useDishaCopy } from '@/lib/disha-copy';
import { CONSTRAINT_NAMES } from '@/lib/disha-events';
import { cn } from '@/lib/shadcn/utils';

function PathBreadcrumb({ path }: { path: string }) {
  return (
    <li className="border-border/70 bg-card flex flex-wrap items-center gap-1 rounded-xl border p-2.5">
      {path.split(' > ').map((part, index) => (
        <span key={`${path}-${part}-${index}`} className="contents">
          {index > 0 && <span className="text-muted-foreground text-xs">›</span>}
          <span className="bg-disha-sun/12 text-foreground rounded-full px-2 py-1 text-xs leading-4">
            {part}
          </span>
        </span>
      ))}
    </li>
  );
}

export function DishaSessionPanel() {
  const { snapshot } = useDishaSession();
  const copy = useDishaCopy();
  const filledConstraintCount = Object.keys(snapshot.constraints).length;

  return (
    <>
      <StrengthCard strengths={snapshot.strengths} />
      <aside
        aria-label={copy.panel.ariaLabel}
        className="border-border/70 bg-disha-paper/85 relative flex min-h-0 flex-col overflow-hidden rounded-[1.75rem] border shadow-[0_20px_60px_-40px_rgba(22,74,71,0.45)] backdrop-blur"
      >
        <div className="border-border/60 flex items-center justify-between border-b px-4 py-3.5 md:px-5">
          <div>
            <p className="text-sm font-semibold">{copy.panel.heading}</p>
            <p className="text-muted-foreground text-xs">{copy.panel.subheading}</p>
          </div>
          {filledConstraintCount > 0 && (
            <span className="bg-disha-leaf/10 text-disha-leaf rounded-full px-2.5 py-1 font-mono text-[11px] font-bold">
              {filledConstraintCount}/5
            </span>
          )}
        </div>

        <div className="min-h-0 flex-1 [scrollbar-width:thin] space-y-5 overflow-y-auto p-4 md:p-5">
          {snapshot.testResult && (
            <section
              aria-labelledby="test-result-title"
              aria-live="polite"
              className="border-disha-leaf/30 bg-disha-leaf/10 rounded-[1.5rem] border p-3.5"
            >
              <div className="flex items-center gap-2">
                <Award className="text-disha-leaf size-4" aria-hidden="true" />
                <h2
                  id="test-result-title"
                  className="text-xs font-bold tracking-[0.12em] uppercase"
                >
                  {copy.panel.testResult}
                </h2>
              </div>
              <p className="text-disha-leaf mt-2 text-sm font-semibold">
                {snapshot.testResult.stream}
              </p>
              <p className="text-muted-foreground mt-1 text-xs leading-5">
                {snapshot.testResult.fit_note}
              </p>
            </section>
          )}

          {snapshot.strengths.length > 0 && (
            <section aria-labelledby="strengths-title" aria-live="polite">
              <div className="mb-3 flex items-center gap-2">
                <Sparkles className="text-disha-sun size-4" aria-hidden="true" />
                <h2 id="strengths-title" className="text-xs font-bold tracking-[0.12em] uppercase">
                  {copy.panel.strengths}
                </h2>
              </div>
              <ul className="space-y-2">
                {snapshot.strengths.map((strength) => (
                  <li
                    key={strength.label}
                    className="border-disha-sun/30 bg-disha-sun/10 rounded-xl border p-3"
                  >
                    <p className="text-sm leading-5 font-semibold">{strength.label}</p>
                    <blockquote className="text-muted-foreground mt-1.5 text-xs leading-5">
                      “{strength.evidence_quote}”
                    </blockquote>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {filledConstraintCount === 0 && (
            <p className="text-muted-foreground px-1 py-6 text-center text-xs leading-5">
              {copy.panel.subheading}
            </p>
          )}

          {filledConstraintCount > 0 && (
            <section aria-labelledby="constraints-title" aria-live="polite">
              <div className="mb-3 flex items-center gap-2">
                <Leaf className="text-disha-leaf size-4" aria-hidden="true" />
                <h2
                  id="constraints-title"
                  className="text-xs font-bold tracking-[0.12em] uppercase"
                >
                  {copy.panel.practicalFit}
                </h2>
              </div>
              <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
                {/* Only what the conversation has actually surfaced. Showing all
                    five empty slots up front turns the panel into the checklist
                    the product promises it is not. */}
                {CONSTRAINT_NAMES.filter((name) => snapshot.constraints[name]).map((name) => {
                  const event = snapshot.constraints[name];
                  return (
                    <li
                      key={name}
                      className="border-disha-leaf/25 bg-disha-leaf/7 flex min-h-16 items-center gap-3 rounded-xl border px-3 py-2.5"
                    >
                      <span
                        className="border-disha-leaf bg-disha-leaf grid size-6 shrink-0 place-items-center rounded-full border text-white"
                        aria-hidden="true"
                      >
                        <Check className="size-3.5" strokeWidth={3} />
                      </span>
                      <span className="min-w-0">
                        <span className="block text-sm leading-4 font-medium">
                          {copy.panel.constraints[name].label}
                        </span>
                        <span className="text-muted-foreground mt-0.5 block truncate text-[11px] leading-4">
                          {event?.value || copy.panel.constraints[name].emptyValue}
                        </span>
                      </span>
                    </li>
                  );
                })}
              </ul>
            </section>
          )}

          {snapshot.careerPaths.length > 0 && (
            <section aria-labelledby="careers-title" aria-live="polite">
              <div className="mb-3 flex items-center gap-2">
                <Route className="text-disha-sun size-4" aria-hidden="true" />
                <h2 id="careers-title" className="text-xs font-bold tracking-[0.12em] uppercase">
                  {copy.panel.careerPaths}
                </h2>
              </div>
              <ul className="space-y-2">
                {snapshot.careerPaths.map((path) => (
                  <PathBreadcrumb key={path} path={path} />
                ))}
              </ul>
            </section>
          )}

          {snapshot.scholarships.length > 0 && (
            <section aria-labelledby="scholarships-title" aria-live="polite">
              <div className="mb-3 flex items-center gap-2">
                <GraduationCap className="text-disha-leaf size-4" aria-hidden="true" />
                <h2
                  id="scholarships-title"
                  className="text-xs font-bold tracking-[0.12em] uppercase"
                >
                  {copy.explore.scholarshipsHeading}
                </h2>
              </div>
              <ul className="space-y-2">
                {snapshot.scholarships.map((scheme) => (
                  <li
                    key={scheme.name}
                    className="border-disha-leaf/25 bg-disha-leaf/7 rounded-xl border p-3"
                  >
                    <p className="text-sm leading-5 font-medium">{scheme.name}</p>
                    {scheme.amount && (
                      <p className="text-muted-foreground mt-1 text-xs leading-5">
                        {copy.explore.amountLabel}: {scheme.amount}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {snapshot.citations.length > 0 && (
            <section aria-labelledby="sources-title" aria-live="polite">
              <div className="mb-3 flex items-center gap-2">
                <BookOpen className="text-disha-leaf size-4" aria-hidden="true" />
                <h2 id="sources-title" className="text-xs font-bold tracking-[0.12em] uppercase">
                  {copy.panel.sources}
                </h2>
              </div>
              <ul className="space-y-1.5">
                {snapshot.citations.map((citation) => (
                  <li
                    key={citation.citation}
                    className="border-border/70 bg-card text-muted-foreground rounded-xl border p-2.5 text-xs leading-5"
                  >
                    <span className="text-foreground font-medium">{citation.source}</span>
                    <span className="ml-1.5 font-mono">
                      {copy.panel.pagePrefix}
                      {citation.page}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {snapshot.flags.length > 0 && (
            <section aria-labelledby="notes-title" aria-live="polite">
              <h2 id="notes-title" className="mb-3 text-xs font-bold tracking-[0.12em] uppercase">
                {copy.panel.attentionNote}
              </h2>
              <ul className="space-y-2">
                {snapshot.flags.map((flag, index) => {
                  const isSelfHarm = flag.flag_type === 'self_harm';
                  return (
                    <li
                      key={`${flag.ts}-${flag.flag_type}-${index}`}
                      className={cn(
                        'rounded-xl border p-3',
                        isSelfHarm
                          ? 'border-red-300 bg-red-50 text-red-950 dark:border-red-900 dark:bg-red-950/40 dark:text-red-100'
                          : 'border-amber-300 bg-amber-50 text-amber-950 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-100'
                      )}
                    >
                      <p className="text-xs font-semibold">{copy.panel.flags[flag.flag_type]}</p>
                      <blockquote className="mt-1.5 text-sm leading-5">“{flag.quote}”</blockquote>
                    </li>
                  );
                })}
              </ul>
            </section>
          )}

          {snapshot.refusals.length > 0 && (
            <section aria-labelledby="refusals-title" aria-live="polite">
              <h2
                id="refusals-title"
                className="mb-2 text-xs font-bold tracking-[0.12em] uppercase"
              >
                {copy.panel.listLimit}
              </h2>
              <ul className="text-muted-foreground space-y-1.5 text-xs leading-5">
                {snapshot.refusals.map((refusal, index) => (
                  <li key={`${refusal.ts}-${index}`}>
                    {copy.panel.refusalPrefix}{' '}
                    <span className="text-foreground font-medium">{refusal.asked_about}</span>{' '}
                    {copy.panel.refusalSuffix}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      </aside>
    </>
  );
}
