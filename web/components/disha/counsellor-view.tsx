'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, DatabaseZap, Lock } from 'lucide-react';
import { DishaBrand } from '@/components/disha/disha-brand';
import { type CaseApiState, type CounsellorSession, mergeSessions } from '@/lib/disha-cases';
import {
  type ConstraintName,
  DISHA_STORAGE_PREFIX,
  type DishaFlagType,
  type StoredDishaSession,
  deriveDishaSnapshot,
  readAllStoredSessions,
} from '@/lib/disha-events';
import { cn } from '@/lib/shadcn/utils';

interface CounsellorViewProps {
  initialSessions: CounsellorSession[];
  apiState: CaseApiState;
}

const CONSTRAINT_LABELS: Record<ConstraintName, string> = {
  distance_from_home: 'दूरी',
  hostel_needed: 'हॉस्टल',
  fee_ceiling: 'फीस',
  family_permission: 'परिवार',
  scholarship_dependence: 'स्कॉलरशिप',
};

const FLAG_LABELS: Record<DishaFlagType, string> = {
  distress: 'सहारे की ज़रूरत',
  family_pressure: 'परिवार का दबाव',
  choice_paralysis: 'फैसले में रुकावट',
  self_harm: 'तुरंत मानवीय संपर्क',
};

const SESSION_DATE_FORMATTER = new Intl.DateTimeFormat('hi-IN', {
  dateStyle: 'medium',
  timeStyle: 'short',
});

function SessionSource({ source }: { source: CounsellorSession['source'] }) {
  return (
    <span
      className={cn(
        'mt-2 inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase',
        source === 'api'
          ? 'bg-disha-leaf/10 text-disha-leaf'
          : 'bg-disha-sun/15 text-amber-800 dark:text-amber-200'
      )}
    >
      {source === 'api' ? 'API' : 'This browser'}
    </span>
  );
}

function ApiNotice({
  apiState,
  browserSessionCount,
}: {
  apiState: CaseApiState;
  browserSessionCount: number;
}) {
  if (apiState === 'ready') return null;

  const fallback =
    browserSessionCount > 0
      ? ' इस browser में save हुए live sessions नीचे दिख रहे हैं।'
      : ' Live session के events इस browser में आते ही यहाँ दिखेंगे।';

  return (
    <div className="border-disha-sun/35 bg-disha-sun/10 mt-6 flex items-start gap-3 rounded-xl border p-3 text-sm">
      {apiState === 'not-configured' ? (
        <>
          <Lock className="text-disha-leaf mt-0.5 size-4 shrink-0" />
          <p>
            <span className="font-medium">DISHA_API_URL</span> set नहीं है, इसलिए server से cases
            नहीं पढ़े गए।{fallback}
          </p>
        </>
      ) : (
        <>
          <DatabaseZap className="text-disha-leaf mt-0.5 size-4 shrink-0" />
          <p>Case API अभी उपलब्ध नहीं है।{fallback}</p>
        </>
      )}
    </div>
  );
}

export function CounsellorView({ initialSessions, apiState }: CounsellorViewProps) {
  const [browserSessions, setBrowserSessions] = useState<StoredDishaSession[]>([]);

  useEffect(() => {
    const refreshBrowserSessions = () => setBrowserSessions(readAllStoredSessions());
    const handleStorage = (event: StorageEvent) => {
      if (event.key?.startsWith(DISHA_STORAGE_PREFIX)) refreshBrowserSessions();
    };

    refreshBrowserSessions();
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, []);

  const sessions = useMemo(
    () => mergeSessions(initialSessions, browserSessions),
    [initialSessions, browserSessions]
  );

  return (
    <main className="bg-disha-wash min-h-svh px-4 py-5 sm:px-6 md:px-8 md:py-8">
      <div className="mx-auto max-w-7xl">
        <div className="flex items-center justify-between gap-4">
          <DishaBrand />
          <Link
            href="/"
            className="border-border/70 bg-card hover:bg-accent focus-visible:ring-ring inline-flex items-center gap-2 rounded-full border px-3 py-2 text-xs font-medium transition-colors focus-visible:ring-2 focus-visible:outline-none"
          >
            <ArrowLeft className="size-3.5" />
            Student view
          </Link>
        </div>

        <header className="mt-10 md:mt-14">
          <p className="text-disha-leaf text-xs font-bold tracking-[0.14em] uppercase">
            Human review
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
            Counsellor sessions
          </h1>
          <p className="text-muted-foreground mt-3 max-w-2xl text-sm leading-6">
            बातचीत में सामने आई practical constraints और वे बातें जिन्हें मानवीय follow-up की ज़रूरत
            हो सकती है।
          </p>
        </header>

        <ApiNotice apiState={apiState} browserSessionCount={browserSessions.length} />

        {sessions.length === 0 ? (
          <section className="border-border/70 bg-card mt-8 rounded-[1.5rem] border border-dashed px-5 py-14 text-center">
            <p className="font-medium">अभी कोई session note नहीं है</p>
            <p className="text-muted-foreground mx-auto mt-2 max-w-md text-sm leading-6">
              Student view में बातचीत शुरू होने पर constraints और review notes इस browser में
              सुरक्षित होकर यहाँ दिखाई देंगे।
            </p>
          </section>
        ) : (
          <div className="border-border/70 bg-card mt-8 overflow-hidden rounded-[1.5rem] border">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[1040px] border-collapse text-left">
                <caption className="sr-only">
                  Disha sessions with signup phones, practical constraints, shortlisted paths, and
                  counsellor review notes
                </caption>
                <thead>
                  <tr className="bg-muted/70 text-muted-foreground text-xs tracking-wide uppercase">
                    <th className="px-5 py-3 font-semibold">Session</th>
                    <th className="px-5 py-3 font-semibold">Phone</th>
                    <th className="px-5 py-3 font-semibold">Constraints</th>
                    <th className="px-5 py-3 font-semibold">Explored</th>
                    <th className="px-5 py-3 font-semibold">Review notes</th>
                    <th className="px-5 py-3 font-semibold">Updated</th>
                  </tr>
                </thead>
                <tbody className="divide-border/60 divide-y">
                  {sessions.map((session) => {
                    const snapshot = deriveDishaSnapshot(session.events);
                    const constraints = Object.values(snapshot.constraints);
                    const shortlist = snapshot.summary?.shortlist ?? [];
                    const explored = shortlist.length > 0 ? shortlist : snapshot.careerPaths;
                    return (
                      <tr key={session.room} className="align-top">
                        <td className="px-5 py-5">
                          <p className="max-w-52 truncate font-mono text-xs font-semibold">
                            {session.room}
                          </p>
                          <SessionSource source={session.source} />
                        </td>
                        <td className="px-5 py-5">
                          {session.signupPhone ? (
                            <>
                              <p className="font-mono text-xs font-semibold whitespace-nowrap">
                                +91 {session.signupPhone}
                              </p>
                              <span className="bg-disha-leaf/10 text-disha-leaf mt-2 inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase">
                                Signed up
                              </span>
                            </>
                          ) : (
                            <span className="text-muted-foreground text-xs">—</span>
                          )}
                        </td>
                        <td className="px-5 py-5">
                          {constraints.length > 0 ? (
                            <ul className="grid max-w-md grid-cols-2 gap-x-4 gap-y-2">
                              {constraints.map((constraint) => (
                                <li key={constraint.name} className="text-xs leading-5">
                                  <span className="text-muted-foreground">
                                    {CONSTRAINT_LABELS[constraint.name]}:
                                  </span>{' '}
                                  <span className="font-medium">{constraint.value}</span>
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <span className="text-muted-foreground text-xs">अभी नहीं मिला</span>
                          )}
                        </td>
                        <td className="px-5 py-5">
                          {explored.length > 0 ? (
                            <ul className="max-w-xs space-y-1.5">
                              {explored.slice(0, 4).map((path, index) => (
                                <li key={`${path}-${index}`} className="text-xs leading-5">
                                  {path}
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <span className="text-muted-foreground text-xs">—</span>
                          )}
                          {snapshot.scholarships.length > 0 && (
                            <p className="text-muted-foreground mt-2 text-[11px]">
                              {snapshot.scholarships.length} scheme
                              {snapshot.scholarships.length === 1 ? '' : 's'} shown
                            </p>
                          )}
                        </td>
                        <td className="px-5 py-5">
                          {snapshot.flags.length > 0 ? (
                            <ul className="max-w-md space-y-2">
                              {snapshot.flags.map((flag, index) => {
                                const isSelfHarm = flag.flag_type === 'self_harm';
                                return (
                                  <li
                                    key={`${flag.ts}-${flag.flag_type}-${index}`}
                                    className={cn(
                                      'rounded-lg border px-3 py-2 text-xs leading-5',
                                      isSelfHarm
                                        ? 'border-red-300 bg-red-50 text-red-950 dark:border-red-900 dark:bg-red-950/40 dark:text-red-100'
                                        : 'border-amber-300 bg-amber-50 text-amber-950 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-100'
                                    )}
                                  >
                                    <span className="font-semibold">
                                      {FLAG_LABELS[flag.flag_type]}
                                    </span>
                                    <span className="mt-0.5 block">“{flag.quote}”</span>
                                  </li>
                                );
                              })}
                            </ul>
                          ) : (
                            <span className="text-muted-foreground text-xs">कोई note नहीं</span>
                          )}
                        </td>
                        <td className="text-muted-foreground px-5 py-5 text-xs whitespace-nowrap">
                          {session.updatedAt
                            ? SESSION_DATE_FORMATTER.format(session.updatedAt)
                            : '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
