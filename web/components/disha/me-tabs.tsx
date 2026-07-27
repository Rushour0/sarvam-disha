'use client';

import { useRef, useState } from 'react';
import Link from 'next/link';
import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Compass,
  FileText,
  GraduationCap,
  Lightbulb,
  MessagesSquare,
  Sparkles,
  Target,
  UserRound,
} from 'lucide-react';
import { Streamdown } from 'streamdown';
import type { DishaSessionSnapshot } from '@/lib/disha-events';
import type { GuideResult } from '@/lib/disha-guide';
import { cn } from '@/lib/shadcn/utils';

const CONSTRAINT_LABELS: Record<string, string> = {
  distance_from_home: 'घर से दूरी',
  hostel_needed: 'Hostel',
  fee_ceiling: 'फीस की सीमा',
  family_permission: 'परिवार की सहमति',
  scholarship_dependence: 'Scholarship पर निर्भरता',
};

const TABS = [
  { id: 'profile', label: 'प्रोफ़ाइल' },
  { id: 'strengths', label: 'Strengths & Test' },
  { id: 'guide', label: 'मेरी Guide' },
] as const;

type TabId = (typeof TABS)[number]['id'];

function SectionCard({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-border/70 bg-card rounded-[1.5rem] border p-5">
      <div className="flex items-center gap-2">
        <span className="text-disha-leaf" aria-hidden="true">
          {icon}
        </span>
        <h2 className="text-sm font-semibold">{title}</h2>
      </div>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function StatTile({ value, label }: { value: string; label: string }) {
  return (
    <div className="border-border/70 bg-disha-paper rounded-2xl border p-4">
      <p className="text-disha-leaf text-2xl leading-none font-semibold tabular-nums">{value}</p>
      <p className="text-muted-foreground mt-1.5 text-xs leading-4">{label}</p>
    </div>
  );
}

/** Renders one markdown block in the guide's warm, plain voice. The prose has
 *  already been link-sanitized server-side, so nothing unexpected renders. */
function GuideProse({ children }: { children: string }) {
  return (
    <div className="[&_a]:text-disha-leaf text-sm leading-6 [&_a]:underline [&_a]:underline-offset-4 [&_p]:mt-2 [&_p:first-child]:mt-0 [&_strong]:font-semibold">
      <Streamdown>{children}</Streamdown>
    </div>
  );
}

function GuideView({ guide }: { guide: GuideResult }) {
  if (!guide.ok) {
    // Missing key or an OpenAI error: still give the student the plain summary
    // and next steps from their call — never a crash, never a blank tab.
    const hasFallback = Boolean(guide.summaryHi) || (guide.nextSteps?.length ?? 0) > 0;
    if (!hasFallback) {
      return (
        <SectionCard icon={<FileText className="size-4" />} title="मेरी Guide">
          <p className="text-muted-foreground text-sm leading-6">
            आपकी personal guide तब बनेगी जब Disha के साथ आपकी बातचीत पूरी होगी। एक बार बात करके आइए
            — फिर यहाँ आपके लिए एक पूरा रास्ता लिखा मिलेगा।
          </p>
        </SectionCard>
      );
    }
    return (
      <SectionCard icon={<CheckCircle2 className="size-4" />} title="आपकी बातचीत का सार">
        {guide.summaryHi && (
          <p className="text-muted-foreground text-sm leading-6">{guide.summaryHi}</p>
        )}
        {guide.nextSteps && guide.nextSteps.length > 0 && (
          <ul className="mt-3 space-y-2">
            {guide.nextSteps.map((step) => (
              <li key={step} className="flex gap-2 text-sm leading-6">
                <ArrowRight className="text-disha-leaf mt-1 size-4 shrink-0" aria-hidden="true" />
                {step}
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
    );
  }

  return (
    <div className="space-y-4">
      <section className="border-border/70 bg-card rounded-[1.5rem] border p-5 sm:p-6">
        <div className="bg-disha-leaf/10 text-disha-leaf inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-semibold">
          <FileText className="size-4" aria-hidden="true" />
          आपके लिए बनी guide
        </div>
        <div className="mt-4">
          <GuideProse>{guide.whoYouAre}</GuideProse>
        </div>
      </section>

      {guide.paths.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-disha-leaf flex items-center gap-2 px-1 text-sm font-semibold">
            <Compass className="size-4" aria-hidden="true" />
            आपके लिए रास्ते
          </h2>
          {guide.paths.map((path) => (
            <article
              key={path.path}
              className="border-border/70 bg-card rounded-[1.5rem] border p-5"
            >
              {path.crumb && <p className="text-muted-foreground text-xs">{path.crumb}</p>}
              <h3 className="mt-0.5 text-base font-semibold">{path.heading}</h3>
              {path.duration && (
                <p className="text-muted-foreground mt-1 text-xs">अवधि: {path.duration}</p>
              )}
              <div className="mt-3">
                <GuideProse>{path.why}</GuideProse>
              </div>
              {path.nextStep && (
                <div className="bg-disha-sun/12 mt-3 rounded-2xl p-3.5">
                  <p className="text-foreground flex items-center gap-1.5 text-xs font-semibold">
                    <Target className="text-disha-leaf size-3.5" aria-hidden="true" />
                    अगला कदम
                  </p>
                  <div className="mt-1.5">
                    <GuideProse>{path.nextStep}</GuideProse>
                  </div>
                </div>
              )}
              {path.link && (
                <a
                  href={path.link}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="text-disha-leaf focus-visible:ring-ring mt-3 inline-flex min-h-11 items-center gap-1.5 rounded-full text-sm font-semibold underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:outline-none"
                >
                  आधिकारिक जानकारी पढ़ें
                  <ArrowRight className="size-4" aria-hidden="true" />
                </a>
              )}
            </article>
          ))}
        </div>
      )}

      {guide.freeStarts.length > 0 && (
        <SectionCard icon={<Lightbulb className="size-4" />} title="मुफ़्त में शुरू करने के रास्ते">
          <ul className="space-y-3">
            {guide.freeStarts.map((start) => (
              <li
                key={start.name}
                className="border-border/70 bg-disha-paper rounded-xl border p-3.5"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-x-2 gap-y-0.5">
                  <p className="text-sm font-semibold">{start.name}</p>
                  {start.cost && (
                    <span className="bg-disha-leaf/10 text-disha-leaf rounded-full px-2 py-0.5 text-[0.65rem] font-semibold">
                      {start.cost}
                    </span>
                  )}
                </div>
                {start.provider && (
                  <p className="text-muted-foreground mt-0.5 text-xs">{start.provider}</p>
                )}
                {start.why && (
                  <div className="mt-2">
                    <GuideProse>{start.why}</GuideProse>
                  </div>
                )}
                {start.url && (
                  <a
                    href={start.url}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="text-disha-leaf mt-2 inline-flex min-h-11 items-center gap-1.5 text-xs font-semibold underline-offset-4 hover:underline"
                  >
                    यहाँ से शुरू करें
                    <ArrowRight className="size-3.5" aria-hidden="true" />
                  </a>
                )}
              </li>
            ))}
          </ul>
        </SectionCard>
      )}

      {guide.close && (
        <section className="border-disha-leaf/20 bg-disha-leaf/5 rounded-[1.5rem] border p-5">
          <GuideProse>{guide.close}</GuideProse>
        </section>
      )}
    </div>
  );
}

export function MeTabs({
  phone,
  snapshot,
  guide,
}: {
  phone: string;
  snapshot: DishaSessionSnapshot;
  guide: GuideResult;
}) {
  const [active, setActive] = useState<TabId>('profile');
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const onKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>, index: number) => {
    let next = index;
    if (event.key === 'ArrowRight' || event.key === 'ArrowDown') next = (index + 1) % TABS.length;
    else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp')
      next = (index - 1 + TABS.length) % TABS.length;
    else if (event.key === 'Home') next = 0;
    else if (event.key === 'End') next = TABS.length - 1;
    else return;
    event.preventDefault();
    setActive(TABS[next].id);
    tabRefs.current[next]?.focus();
  };

  const constraintCount = Object.keys(snapshot.constraints).length;
  const interests = snapshot.profile?.interests ?? [];

  return (
    <div className="mt-6">
      {/* Sticky, thumb-friendly segmented control. */}
      <div className="bg-disha-wash/85 sticky top-0 z-10 -mx-4 px-4 py-2 backdrop-blur sm:-mx-6 sm:px-6">
        <div
          role="tablist"
          aria-label="प्रोफ़ाइल के हिस्से"
          className="border-border/70 bg-card flex gap-1 rounded-full border p-1"
        >
          {TABS.map((tab, index) => {
            const selected = active === tab.id;
            return (
              <button
                key={tab.id}
                ref={(node) => {
                  tabRefs.current[index] = node;
                }}
                type="button"
                role="tab"
                id={`me-tab-${tab.id}`}
                aria-selected={selected}
                aria-controls={`me-panel-${tab.id}`}
                tabIndex={selected ? 0 : -1}
                onClick={() => setActive(tab.id)}
                onKeyDown={(event) => onKeyDown(event, index)}
                className={cn(
                  'flex min-h-11 flex-1 items-center justify-center rounded-full px-2 text-center text-xs font-semibold transition-colors motion-reduce:transition-none sm:text-sm',
                  'focus-visible:ring-disha-leaf focus-visible:ring-2 focus-visible:outline-none',
                  selected
                    ? 'bg-disha-leaf text-white shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Profile tab: identity header + interests + constraints + career matches + transcript. */}
      <div
        role="tabpanel"
        id="me-panel-profile"
        aria-labelledby="me-tab-profile"
        hidden={active !== 'profile'}
        tabIndex={0}
        className="mt-4 space-y-4 focus:outline-none"
      >
        <header className="border-border/70 bg-card rounded-[2rem] border p-5 sm:p-7">
          <div className="bg-disha-leaf/10 text-disha-leaf inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-semibold">
            <UserRound className="size-4" aria-hidden="true" />
            Disha की बातचीत से बनी profile
          </div>
          <h1 className="mt-4 text-2xl font-semibold tracking-tight sm:text-3xl">
            {snapshot.profile?.name ?? `+91 ${phone}`}
          </h1>
          <dl className="text-muted-foreground mt-3 flex flex-wrap gap-x-6 gap-y-1 text-sm">
            {snapshot.profile?.class_level && (
              <div className="flex gap-2">
                <dt>कक्षा:</dt>
                <dd className="text-foreground font-medium">{snapshot.profile.class_level}</dd>
              </div>
            )}
            {snapshot.profile?.stream && (
              <div className="flex gap-2">
                <dt>Stream:</dt>
                <dd className="text-foreground font-medium">{snapshot.profile.stream}</dd>
              </div>
            )}
            <div className="flex gap-2">
              <dt>मोबाइल:</dt>
              <dd className="text-foreground font-medium">+91 {phone}</dd>
            </div>
          </dl>
          {interests.length > 0 && (
            <ul className="mt-3 flex flex-wrap gap-1.5">
              {interests.map((interest) => (
                <li
                  key={interest}
                  className="bg-disha-sun/12 rounded-full px-2.5 py-1 text-xs leading-4"
                >
                  {interest}
                </li>
              ))}
            </ul>
          )}
        </header>

        {constraintCount > 0 && (
          <SectionCard icon={<BookOpen className="size-4" />} title="आपकी परिस्थितियाँ">
            <dl className="space-y-1.5">
              {Object.entries(snapshot.constraints).map(([name, constraint]) => (
                <div key={name} className="flex gap-2 text-sm leading-6">
                  <dt className="text-muted-foreground shrink-0">
                    {CONSTRAINT_LABELS[name] ?? name}:
                  </dt>
                  <dd className="font-medium">{constraint?.value}</dd>
                </div>
              ))}
            </dl>
          </SectionCard>
        )}

        {snapshot.careerMatches.length > 0 && (
          <SectionCard icon={<Compass className="size-4" />} title="बातचीत में मिले रास्ते">
            <ul className="space-y-2">
              {snapshot.careerMatches.map((match) => {
                const parts = match.path.split(' > ');
                return (
                  <li
                    key={match.path}
                    className="border-border/70 bg-disha-paper rounded-xl border p-3"
                  >
                    <p className="text-muted-foreground text-xs">
                      {parts.slice(0, -1).join(' › ')}
                    </p>
                    <p className="mt-0.5 text-sm font-semibold">{parts[parts.length - 1]}</p>
                    {match.duration && (
                      <p className="text-muted-foreground mt-1 text-xs">अवधि: {match.duration}</p>
                    )}
                    {match.link && (
                      <a
                        href={match.link}
                        target="_blank"
                        rel="noreferrer noopener"
                        className="text-disha-leaf mt-1 inline-block text-xs font-semibold underline-offset-4 hover:underline"
                      >
                        आधिकारिक जानकारी पढ़ें
                      </a>
                    )}
                  </li>
                );
              })}
            </ul>
          </SectionCard>
        )}

        {snapshot.utterances.length > 0 && (
          <SectionCard icon={<MessagesSquare className="size-4" />} title="बातचीत का record">
            <ol className="max-h-96 space-y-2 overflow-y-auto pr-1">
              {snapshot.utterances.map((utterance, index) => (
                <li
                  key={`${utterance.ts}-${index}`}
                  className={cn(
                    'max-w-[85%] rounded-2xl px-3.5 py-2 text-sm leading-6',
                    utterance.role === 'disha'
                      ? 'bg-disha-leaf/10 rounded-bl-sm'
                      : 'bg-disha-sun/12 ml-auto rounded-br-sm'
                  )}
                >
                  <p className="text-muted-foreground text-[0.65rem] font-semibold tracking-wide uppercase">
                    {utterance.role === 'disha' ? 'Disha' : (snapshot.profile?.name ?? 'आप')}
                  </p>
                  {utterance.text}
                </li>
              ))}
            </ol>
          </SectionCard>
        )}
      </div>

      {/* Strengths & Test tab: metrics row + strengths + test result. */}
      <div
        role="tabpanel"
        id="me-panel-strengths"
        aria-labelledby="me-tab-strengths"
        hidden={active !== 'strengths'}
        tabIndex={0}
        className="mt-4 space-y-4 focus:outline-none"
      >
        <section className="border-border/70 bg-card rounded-[1.5rem] border p-5">
          <div className="flex items-center gap-2">
            <span className="text-disha-leaf" aria-hidden="true">
              <Target className="size-4" />
            </span>
            <h2 className="text-sm font-semibold">आपकी प्रगति</h2>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatTile value={`${constraintCount} / 5`} label="परिस्थितियाँ भरीं" />
            <StatTile value={String(snapshot.careerMatches.length)} label="रास्ते देखे" />
            <StatTile value={String(snapshot.decisions.length)} label="फ़ैसले लिए" />
            <StatTile value={String(snapshot.strengths.length)} label="strengths मिलीं" />
          </div>
        </section>

        {snapshot.strengths.length > 0 && (
          <SectionCard icon={<Sparkles className="size-4" />} title="आपकी strengths">
            <ul className="space-y-3">
              {snapshot.strengths.map((strength) => (
                <li key={strength.label}>
                  <p className="text-sm font-medium">{strength.label}</p>
                  <blockquote className="text-muted-foreground mt-1 border-l-2 pl-3 text-sm leading-6">
                    “{strength.evidence_quote}”
                  </blockquote>
                </li>
              ))}
            </ul>
          </SectionCard>
        )}

        {snapshot.testResult && (
          <SectionCard icon={<GraduationCap className="size-4" />} title="Test का नतीजा">
            <p className="text-sm">
              <span className="bg-disha-leaf/10 text-disha-leaf rounded-full px-2.5 py-1 text-xs font-semibold">
                {snapshot.testResult.stream}
              </span>
            </p>
            <p className="text-muted-foreground mt-2 text-sm leading-6">
              {snapshot.testResult.fit_note}
            </p>
            {snapshot.testResult.evidence.length > 0 && (
              <ul className="mt-3 space-y-1.5">
                {snapshot.testResult.evidence.map((line) => (
                  <li key={line} className="flex gap-2 text-sm leading-6">
                    <CheckCircle2
                      className="text-disha-leaf mt-1 size-4 shrink-0"
                      aria-hidden="true"
                    />
                    {line}
                  </li>
                ))}
              </ul>
            )}
          </SectionCard>
        )}

        {snapshot.strengths.length === 0 && !snapshot.testResult && (
          <SectionCard icon={<Sparkles className="size-4" />} title="आपकी strengths">
            <p className="text-muted-foreground text-sm leading-6">
              अभी strengths और test का नतीजा नहीं बना। Disha के साथ थोड़ा और बात करके आइए।
            </p>
          </SectionCard>
        )}
      </div>

      {/* My Guide tab: the auto-generated, grounded career document. */}
      <div
        role="tabpanel"
        id="me-panel-guide"
        aria-labelledby="me-tab-guide"
        hidden={active !== 'guide'}
        tabIndex={0}
        className="mt-4 focus:outline-none"
      >
        <GuideView guide={guide} />
      </div>

      <div className="border-border/70 bg-card mt-4 rounded-[1.5rem] border p-5 text-center">
        <p className="text-muted-foreground text-sm leading-6">
          और रास्ते देखने हैं? पूरा career index खुला है।
        </p>
        <Link
          href="/explore"
          className="text-disha-leaf mt-2 inline-flex min-h-11 items-center gap-1.5 text-sm font-semibold underline-offset-4 hover:underline"
        >
          Career index खोलें
          <ArrowRight className="size-4" aria-hidden="true" />
        </Link>
      </div>
    </div>
  );
}
