import type { Metadata } from 'next';
import { cookies } from 'next/headers';
import Link from 'next/link';
import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Compass,
  GraduationCap,
  MessagesSquare,
  Sparkles,
  UserRound,
} from 'lucide-react';
import { DishaBrand } from '@/components/disha/disha-brand';
import { LoginCard } from '@/components/disha/login-card';
import {
  type DishaSessionSnapshot,
  deriveDishaSnapshot,
  parseDishaEvent,
} from '@/lib/disha-events';
import { cn } from '@/lib/shadcn/utils';

export const metadata: Metadata = {
  title: 'मेरी प्रोफ़ाइल — Disha',
  description: 'Disha से हुई बातचीत में बनी आपकी profile — strengths, रास्ते और अगले कदम।',
};

// The profile is rebuilt from the case file on every visit — a call may have
// just ended, and a cached page would hide exactly that call.
export const dynamic = 'force-dynamic';

const API_ORIGIN = process.env.DISHA_API_ORIGIN ?? 'http://sarvam-api:8090';

const CONSTRAINT_LABELS: Record<string, string> = {
  distance_from_home: 'घर से दूरी',
  hostel_needed: 'Hostel',
  fee_ceiling: 'फीस की सीमा',
  family_permission: 'परिवार की सहमति',
  scholarship_dependence: 'Scholarship पर निर्भरता',
};

interface MeResponse {
  phone: string;
  snapshot: DishaSessionSnapshot;
}

async function fetchMe(): Promise<MeResponse | null> {
  const sessionCookie = (await cookies()).get('disha_session');
  if (!sessionCookie) return null;

  try {
    const response = await fetch(`${API_ORIGIN}/me`, {
      cache: 'no-store',
      headers: { cookie: `disha_session=${sessionCookie.value}` },
    });
    if (!response.ok) return null;

    const data: unknown = await response.json();
    if (typeof data !== 'object' || data === null) return null;
    const record = data as { phone?: unknown; events?: unknown };
    if (typeof record.phone !== 'string' || !Array.isArray(record.events)) return null;

    const events = record.events.map(parseDishaEvent).filter((event) => event !== null);
    return { phone: record.phone, snapshot: deriveDishaSnapshot(events) };
  } catch {
    return null;
  }
}

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

export default async function MePage() {
  const me = await fetchMe();

  return (
    <main className="bg-disha-wash min-h-svh">
      <div className="mx-auto w-full max-w-3xl px-4 py-6 sm:px-6 md:py-10">
        <div className="flex items-center justify-between">
          <DishaBrand />
          <Link
            href="/"
            className="text-disha-leaf focus-visible:ring-ring min-h-11 rounded-full px-3 py-3 text-sm font-medium underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:outline-none"
          >
            नई बातचीत
          </Link>
        </div>

        {!me ? (
          <div className="mt-10 max-w-md">
            <h1 className="text-2xl font-semibold tracking-tight">मेरी प्रोफ़ाइल</h1>
            <p className="text-muted-foreground mt-2 text-sm leading-6">
              Disha से बात करने के बाद आपकी profile यहाँ बनती है — आपकी strengths, चुने हुए रास्ते
              और अगले कदम।
            </p>
            <div className="mt-6">
              <LoginCard
                title="अपनी profile देखने के लिए login करें"
                body="वही मोबाइल नंबर डालें जो आपने Disha को बातचीत में दिया था।"
              />
            </div>
          </div>
        ) : (
          <div className="mt-8 space-y-4">
            <header className="border-border/70 bg-card rounded-[2rem] border p-5 sm:p-7">
              <div className="bg-disha-leaf/10 text-disha-leaf inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-semibold">
                <UserRound className="size-4" aria-hidden="true" />
                Disha की बातचीत से बनी profile
              </div>
              <h1 className="mt-4 text-2xl font-semibold tracking-tight sm:text-3xl">
                {me.snapshot.profile?.name ?? `+91 ${me.phone}`}
              </h1>
              <dl className="text-muted-foreground mt-3 flex flex-wrap gap-x-6 gap-y-1 text-sm">
                {me.snapshot.profile?.class_level && (
                  <div className="flex gap-2">
                    <dt>कक्षा:</dt>
                    <dd className="text-foreground font-medium">
                      {me.snapshot.profile.class_level}
                    </dd>
                  </div>
                )}
                {me.snapshot.profile?.stream && (
                  <div className="flex gap-2">
                    <dt>Stream:</dt>
                    <dd className="text-foreground font-medium">{me.snapshot.profile.stream}</dd>
                  </div>
                )}
                <div className="flex gap-2">
                  <dt>मोबाइल:</dt>
                  <dd className="text-foreground font-medium">+91 {me.phone}</dd>
                </div>
              </dl>
              {me.snapshot.profile?.interests && me.snapshot.profile.interests.length > 0 && (
                <ul className="mt-3 flex flex-wrap gap-1.5">
                  {me.snapshot.profile.interests.map((interest) => (
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

            {me.snapshot.strengths.length > 0 && (
              <SectionCard icon={<Sparkles className="size-4" />} title="आपकी strengths">
                <ul className="space-y-3">
                  {me.snapshot.strengths.map((strength) => (
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

            {me.snapshot.testResult && (
              <SectionCard icon={<GraduationCap className="size-4" />} title="Test का नतीजा">
                <p className="text-sm">
                  <span className="bg-disha-leaf/10 text-disha-leaf rounded-full px-2.5 py-1 text-xs font-semibold">
                    {me.snapshot.testResult.stream}
                  </span>
                </p>
                <p className="text-muted-foreground mt-2 text-sm leading-6">
                  {me.snapshot.testResult.fit_note}
                </p>
              </SectionCard>
            )}

            {me.snapshot.summary && (
              <SectionCard icon={<CheckCircle2 className="size-4" />} title="पिछली बातचीत का सार">
                <p className="text-muted-foreground text-sm leading-6">
                  {me.snapshot.summary.summary_hi}
                </p>
                {me.snapshot.summary.next_steps.length > 0 && (
                  <ul className="mt-3 space-y-2">
                    {me.snapshot.summary.next_steps.map((step) => (
                      <li key={step} className="flex gap-2 text-sm leading-6">
                        <ArrowRight
                          className="text-disha-leaf mt-1 size-4 shrink-0"
                          aria-hidden="true"
                        />
                        {step}
                      </li>
                    ))}
                  </ul>
                )}
              </SectionCard>
            )}

            {me.snapshot.careerMatches.length > 0 && (
              <SectionCard icon={<Compass className="size-4" />} title="बातचीत में मिले रास्ते">
                <ul className="space-y-2">
                  {me.snapshot.careerMatches.map((match) => {
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
                          <p className="text-muted-foreground mt-1 text-xs">
                            अवधि: {match.duration}
                          </p>
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

            {Object.keys(me.snapshot.constraints).length > 0 && (
              <SectionCard icon={<BookOpen className="size-4" />} title="आपकी परिस्थितियाँ">
                <dl className="space-y-1.5">
                  {Object.entries(me.snapshot.constraints).map(([name, constraint]) => (
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

            {me.snapshot.utterances.length > 0 && (
              <SectionCard icon={<MessagesSquare className="size-4" />} title="बातचीत का record">
                <ol className="max-h-96 space-y-2 overflow-y-auto pr-1">
                  {me.snapshot.utterances.map((utterance, index) => (
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
                        {utterance.role === 'disha' ? 'Disha' : (me.snapshot.profile?.name ?? 'आप')}
                      </p>
                      {utterance.text}
                    </li>
                  ))}
                </ol>
              </SectionCard>
            )}

            <div className="border-border/70 bg-card rounded-[1.5rem] border p-5 text-center">
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
        )}
      </div>
    </main>
  );
}
