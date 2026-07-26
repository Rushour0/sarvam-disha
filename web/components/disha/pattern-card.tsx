'use client';

import { Award, Compass, Sparkles } from 'lucide-react';
import { useDishaCopy } from '@/lib/disha-copy';
import { CONSTRAINT_NAMES, type DishaSessionSnapshot } from '@/lib/disha-events';

/**
 * The shape the conversation drew of one student.
 *
 * Strengths are quoted back with the student's own words as evidence, and the
 * constraints are reframed as what they weigh rather than what limits them —
 * the same five facts, read as a portrait instead of a rejection list.
 */
export function PatternCard({ snapshot }: { snapshot: DishaSessionSnapshot }) {
  const copy = useDishaCopy();
  const weighed = CONSTRAINT_NAMES.map((name) => snapshot.constraints[name]).filter(
    (constraint) => constraint !== undefined
  );
  const hasPattern =
    snapshot.strengths.length > 0 || weighed.length > 0 || snapshot.testResult !== undefined;

  return (
    <section
      aria-labelledby="pattern-heading"
      className="border-border/70 bg-card rounded-[2rem] border p-5 sm:p-7"
    >
      <div className="flex items-center gap-2">
        <Compass className="text-disha-leaf size-4" aria-hidden="true" />
        <h2 id="pattern-heading" className="text-sm font-semibold">
          {copy.pattern.heading}
        </h2>
      </div>
      <p className="text-muted-foreground mt-1.5 text-sm leading-6">{copy.pattern.subheading}</p>

      {!hasPattern && (
        <p className="text-muted-foreground mt-5 text-sm leading-6">{copy.pattern.empty}</p>
      )}

      {snapshot.strengths.length > 0 && (
        <div className="mt-6">
          <div className="flex items-center gap-2">
            <Sparkles className="text-disha-sun size-4" aria-hidden="true" />
            <h3 className="text-xs font-bold tracking-[0.12em] uppercase">
              {copy.pattern.strengthsHeading}
            </h3>
          </div>
          <ul className="mt-3 grid gap-2 sm:grid-cols-2">
            {snapshot.strengths.map((strength) => (
              <li
                key={strength.label}
                className="border-disha-sun/30 bg-disha-sun/10 rounded-[1.25rem] border p-4"
              >
                <p className="text-disha-leaf leading-6 font-semibold">{strength.label}</p>
                <blockquote className="text-muted-foreground mt-1.5 text-sm leading-6">
                  “{strength.evidence_quote}”
                </blockquote>
              </li>
            ))}
          </ul>
        </div>
      )}

      {weighed.length > 0 && (
        <div className="mt-6">
          <h3 className="text-xs font-bold tracking-[0.12em] uppercase">
            {copy.pattern.weighsHeading}
          </h3>
          <ul className="mt-3 flex flex-wrap gap-2">
            {weighed.map((constraint) => (
              <li
                key={constraint.name}
                className="border-disha-leaf/25 bg-disha-leaf/7 rounded-full border px-3.5 py-2 text-sm leading-5"
              >
                <span className="text-muted-foreground">
                  {copy.panel.constraints[constraint.name].label}
                </span>{' '}
                <span className="font-medium">{constraint.value}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {snapshot.testResult && (
        <div className="border-disha-leaf/30 bg-disha-leaf/10 mt-6 rounded-[1.25rem] border p-4">
          <div className="flex items-center gap-2">
            <Award className="text-disha-leaf size-4" aria-hidden="true" />
            <h3 className="text-xs font-bold tracking-[0.12em] uppercase">
              {copy.pattern.testHeading}
            </h3>
          </div>
          <p className="text-disha-leaf mt-3 font-semibold">{snapshot.testResult.stream}</p>
          <p className="text-muted-foreground mt-1 text-sm leading-6">
            {snapshot.testResult.fit_note}
          </p>
        </div>
      )}
    </section>
  );
}
