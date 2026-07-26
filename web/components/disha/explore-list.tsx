'use client';

import type { ReactNode } from 'react';
import { BookOpen, ExternalLink, GraduationCap, Landmark, Route } from 'lucide-react';
import { useDishaCopy } from '@/lib/disha-copy';
import type { CareerMatch, DishaSessionSnapshot, ScholarshipScheme } from '@/lib/disha-events';
import { sourcesForStates } from '@/lib/disha-sources';

/** How much of the reference material is readable before signing up. A student
 *  who gets nothing has no reason to trust the ask; a student who gets
 *  everything has no reason to answer it. */
const FREE_PATH_LINKS = 2;
const FREE_SCHOLARSHIPS = 1;

interface ExploreListProps {
  snapshot: DishaSessionSnapshot;
  unlocked: boolean;
  /** Rendered in place of the withheld material while `unlocked` is false. */
  gate: ReactNode;
}

function SourceLink({ href, label }: { href: string; label: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer noopener"
      className="text-disha-leaf focus-visible:ring-ring mt-3 inline-flex min-h-11 items-center gap-1.5 text-sm font-semibold underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:outline-none"
    >
      {label}
      <ExternalLink className="size-3.5" aria-hidden="true" />
    </a>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2 text-sm leading-6">
      <dt className="text-muted-foreground shrink-0">{label}</dt>
      <dd className="font-medium">{value}</dd>
    </div>
  );
}

function PathCard({ match, showLink }: { match: CareerMatch; showLink: boolean }) {
  const copy = useDishaCopy();
  const parts = match.path.split(' > ');
  const name = parts[parts.length - 1];

  return (
    <li className="border-border/70 bg-disha-paper rounded-[1.25rem] border p-4">
      <p className="text-muted-foreground text-xs leading-5">{parts.slice(0, -1).join(' › ')}</p>
      <h4 className="mt-0.5 leading-6 font-semibold">{name}</h4>

      <dl className="mt-3 space-y-1">
        {match.level && <DetailRow label={copy.explore.levelLabel} value={match.level} />}
        {match.duration && <DetailRow label={copy.explore.durationLabel} value={match.duration} />}
        {match.state && <DetailRow label={copy.explore.stateLabel} value={match.state} />}
        {match.jobs && <DetailRow label={copy.explore.jobsLabel} value={match.jobs} />}
        {match.eligibility && (
          <DetailRow label={copy.explore.eligibilityLabel} value={match.eligibility} />
        )}
      </dl>

      {match.note && <p className="text-muted-foreground mt-2 text-sm leading-6">{match.note}</p>}

      {match.children.length > 0 && (
        <div className="mt-3">
          <p className="text-muted-foreground text-xs">{copy.explore.leadsToLabel}</p>
          <ul className="mt-1.5 flex flex-wrap gap-1.5">
            {match.children.map((child) => (
              <li
                key={child}
                className="bg-disha-sun/12 rounded-full px-2.5 py-1 text-xs leading-4"
              >
                {child}
              </li>
            ))}
          </ul>
        </div>
      )}

      {match.link && showLink && <SourceLink href={match.link} label={copy.explore.openLink} />}
    </li>
  );
}

function ScholarshipCard({ scheme }: { scheme: ScholarshipScheme }) {
  const copy = useDishaCopy();

  return (
    <li className="border-disha-leaf/25 bg-disha-leaf/7 rounded-[1.25rem] border p-4">
      <h4 className="leading-6 font-semibold">{scheme.name}</h4>
      <p className="text-muted-foreground mt-0.5 text-xs leading-5">{scheme.provider}</p>

      <dl className="mt-3 space-y-1">
        {scheme.amount && <DetailRow label={copy.explore.amountLabel} value={scheme.amount} />}
        {scheme.income_ceiling && (
          <DetailRow label={copy.explore.incomeCeilingLabel} value={scheme.income_ceiling} />
        )}
        {scheme.state && <DetailRow label={copy.explore.stateLabel} value={scheme.state} />}
      </dl>

      {scheme.eligibility && (
        <p className="text-muted-foreground mt-2 text-sm leading-6">{scheme.eligibility}</p>
      )}
      {scheme.source_url && <SourceLink href={scheme.source_url} label={copy.explore.openLink} />}
    </li>
  );
}

export function ExploreList({ snapshot, unlocked, gate }: ExploreListProps) {
  const copy = useDishaCopy();

  const states = [
    ...snapshot.careerMatches.map((match) => match.state ?? ''),
    ...snapshot.scholarships.map((scheme) => scheme.state ?? ''),
  ];
  const sources = sourcesForStates(states);
  const shownScholarships = unlocked
    ? snapshot.scholarships
    : snapshot.scholarships.slice(0, FREE_SCHOLARSHIPS);
  const linkablePaths = snapshot.careerMatches.filter((match) => match.link).length;

  const withheld = unlocked
    ? 0
    : Math.max(0, linkablePaths - FREE_PATH_LINKS) +
      Math.max(0, snapshot.scholarships.length - FREE_SCHOLARSHIPS) +
      snapshot.citations.length +
      sources.length;

  const hasAnything =
    snapshot.careerMatches.length > 0 ||
    snapshot.scholarships.length > 0 ||
    snapshot.citations.length > 0;

  if (!hasAnything) {
    return (
      <section className="border-border/70 bg-card rounded-[2rem] border border-dashed p-5 sm:p-7">
        <h2 className="text-sm font-semibold">{copy.explore.heading}</h2>
        <p className="text-muted-foreground mt-2 text-sm leading-6">{copy.explore.empty}</p>
      </section>
    );
  }

  let linkBudget = unlocked ? Number.POSITIVE_INFINITY : FREE_PATH_LINKS;

  return (
    <section
      aria-labelledby="explore-heading"
      className="border-border/70 bg-card rounded-[2rem] border p-5 sm:p-7"
    >
      <div className="flex items-center gap-2">
        <BookOpen className="text-disha-leaf size-4" aria-hidden="true" />
        <h2 id="explore-heading" className="text-sm font-semibold">
          {copy.explore.heading}
        </h2>
      </div>
      <p className="text-muted-foreground mt-1.5 text-sm leading-6">{copy.explore.subheading}</p>

      {snapshot.careerMatches.length > 0 && (
        <div className="mt-6">
          <div className="mb-3 flex items-center gap-2">
            <Route className="text-disha-sun size-4" aria-hidden="true" />
            <h3 className="text-xs font-bold tracking-[0.12em] uppercase">
              {copy.explore.pathsHeading}
            </h3>
          </div>
          <ul className="grid gap-3 sm:grid-cols-2">
            {snapshot.careerMatches.map((match) => {
              const showLink = Boolean(match.link) && linkBudget > 0;
              if (showLink) linkBudget -= 1;
              return <PathCard key={match.path} match={match} showLink={showLink} />;
            })}
          </ul>
        </div>
      )}

      {shownScholarships.length > 0 && (
        <div className="mt-6">
          <div className="mb-3 flex items-center gap-2">
            <GraduationCap className="text-disha-leaf size-4" aria-hidden="true" />
            <h3 className="text-xs font-bold tracking-[0.12em] uppercase">
              {copy.explore.scholarshipsHeading}
            </h3>
          </div>
          <ul className="grid gap-3 sm:grid-cols-2">
            {shownScholarships.map((scheme) => (
              <ScholarshipCard key={scheme.name} scheme={scheme} />
            ))}
          </ul>
        </div>
      )}

      {unlocked && snapshot.citations.length > 0 && (
        <div className="mt-6">
          <div className="mb-3 flex items-center gap-2">
            <BookOpen className="text-disha-leaf size-4" aria-hidden="true" />
            <h3 className="text-xs font-bold tracking-[0.12em] uppercase">
              {copy.explore.readingHeading}
            </h3>
          </div>
          <ul className="space-y-2">
            {snapshot.citations.map((citation) => (
              <li
                key={citation.citation}
                className="border-border/70 bg-disha-paper rounded-[1.25rem] border p-4"
              >
                {citation.text && (
                  <blockquote className="text-sm leading-6">“{citation.text}”</blockquote>
                )}
                <p className="text-muted-foreground mt-2 text-xs">
                  {citation.source} · {copy.explore.pagePrefix} {citation.page}
                </p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {unlocked && sources.length > 0 && (
        <div className="mt-6">
          <div className="mb-3 flex items-center gap-2">
            <Landmark className="text-disha-leaf size-4" aria-hidden="true" />
            <h3 className="text-xs font-bold tracking-[0.12em] uppercase">
              {copy.explore.sourcesHeading}
            </h3>
          </div>
          <ul className="grid gap-2 sm:grid-cols-2">
            {sources.map((source) => (
              <li
                key={source.url}
                className="border-border/70 bg-disha-paper rounded-xl border px-4 py-3"
              >
                <a
                  href={source.url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="focus-visible:ring-ring inline-flex items-center gap-1.5 text-sm leading-5 font-medium underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:outline-none"
                >
                  {source.title}
                  <ExternalLink className="size-3.5 shrink-0" aria-hidden="true" />
                </a>
                <p className="text-muted-foreground mt-0.5 text-xs leading-5">{source.note}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {withheld > 0 && <div className="mt-6">{gate}</div>}
    </section>
  );
}
