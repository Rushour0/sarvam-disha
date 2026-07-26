'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, DatabaseZap } from 'lucide-react';
import { DishaBrand } from '@/components/disha/disha-brand';
import {
  type ConstraintName,
  DISHA_STORAGE_PREFIX,
  type DishaEvent,
  type DishaFlagType,
  type StoredDishaSession,
  deriveDishaSnapshot,
  parseDishaEvent,
  readAllStoredSessions,
} from '@/lib/disha-events';
import { cn } from '@/lib/shadcn/utils';

interface CounsellorSession extends StoredDishaSession {
  source: 'api' | 'browser';
  signupPhone: string | null;
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function extractRoom(value: unknown): string {
  if (typeof value === 'string') return value;
  if (!isRecord(value)) return '';

  for (const key of ['room', 'room_name', 'id', 'name']) {
    if (typeof value[key] === 'string') return value[key];
  }
  return '';
}

function timestampToMilliseconds(value: unknown): number {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value < 10_000_000_000 ? value * 1000 : value;
  }
  if (typeof value === 'string') {
    const parsed = Date.parse(value);
    return Number.isNaN(parsed) ? 0 : parsed;
  }
  return 0;
}

function extractEvents(value: unknown): DishaEvent[] {
  if (!isRecord(value)) return [];

  const rawEvents = Array.isArray(value.events)
    ? value.events
    : Array.isArray(value.timeline)
      ? value.timeline
      : [];
  const events = rawEvents.map(parseDishaEvent).filter((event) => event !== null);

  if (isRecord(value.constraints)) {
    for (const [name, constraintValue] of Object.entries(value.constraints)) {
      const rawValue = isRecord(constraintValue) ? constraintValue.value : constraintValue;
      const parsed = parseDishaEvent({
        type: 'constraint',
        ts: isRecord(constraintValue) ? (constraintValue.ts ?? 0) : 0,
        name,
        value: rawValue,
      });
      if (parsed) events.push(parsed);
    }
  } else if (Array.isArray(value.constraints)) {
    for (const constraint of value.constraints) {
      if (!isRecord(constraint)) continue;
      const parsed = parseDishaEvent({
        type: 'constraint',
        ts: constraint.ts ?? 0,
        name: constraint.name,
        value: constraint.value,
      });
      if (parsed) events.push(parsed);
    }
  }

  if (Array.isArray(value.flags)) {
    for (const flag of value.flags) {
      if (!isRecord(flag)) continue;
      const parsed = parseDishaEvent({
        type: 'flag',
        ts: flag.ts ?? 0,
        flag_type: flag.flag_type ?? flag.flag,
        quote: flag.quote,
      });
      if (parsed) events.push(parsed);
    }
  }

  return events;
}

function extractSignupPhone(value: unknown): string | null {
  if (!isRecord(value)) return null;
  const caseValue = isRecord(value.case) ? value.case : value;
  return typeof caseValue.phone === 'string' ? caseValue.phone : null;
}

function normaliseApiSession(
  value: unknown,
  fallbackRoom = '',
  fallbackSignupPhone: string | null = null,
  fallbackUpdatedAt = 0
): CounsellorSession | null {
  if (!isRecord(value)) return null;

  const caseValue = isRecord(value.case) ? value.case : value;
  const room = extractRoom(caseValue) || fallbackRoom;
  if (!room) return null;

  const events = extractEvents(caseValue);
  const latestEvent = events.reduce((latest, event) => Math.max(latest, event.ts * 1000), 0);
  const updatedAt =
    timestampToMilliseconds(
      caseValue.updated_at ?? caseValue.updatedAt ?? caseValue.updated ?? caseValue.ts
    ) ||
    latestEvent ||
    fallbackUpdatedAt;

  return {
    room,
    events,
    updatedAt,
    source: 'api',
    signupPhone: extractSignupPhone(caseValue) ?? fallbackSignupPhone,
  };
}

function extractCaseList(value: unknown): unknown[] {
  if (Array.isArray(value)) return value;
  if (isRecord(value) && Array.isArray(value.cases)) return value.cases;
  return [];
}

async function fetchApiSessions(signal: AbortSignal): Promise<CounsellorSession[]> {
  const configuredBase = process.env.NEXT_PUBLIC_DISHA_API?.trim();
  if (!configuredBase) throw new Error('API not configured');

  const base = configuredBase.replace(/\/+$/, '');
  const casesResponse = await fetch(`${base}/cases`, { cache: 'no-store', signal });
  if (!casesResponse.ok) throw new Error(`Cases request failed: ${casesResponse.status}`);

  const caseList = extractCaseList(await casesResponse.json());
  const sessions = await Promise.all(
    caseList.map(async (caseEntry) => {
      const room = extractRoom(caseEntry);
      if (!room) return null;
      const signupPhone = extractSignupPhone(caseEntry);
      const updatedAt = isRecord(caseEntry)
        ? timestampToMilliseconds(
            caseEntry.updated_at ?? caseEntry.updatedAt ?? caseEntry.updated ?? caseEntry.ts
          )
        : 0;

      try {
        const detailResponse = await fetch(`${base}/cases/${encodeURIComponent(room)}`, {
          cache: 'no-store',
          signal,
        });
        if (detailResponse.ok) {
          return normaliseApiSession(await detailResponse.json(), room, signupPhone, updatedAt);
        }
      } catch (error) {
        if (signal.aborted) throw error;
      }

      return normaliseApiSession(caseEntry, room, signupPhone, updatedAt);
    })
  );

  return sessions.filter((session) => session !== null);
}

function mergeSessions(
  apiSessions: CounsellorSession[],
  browserSessions: StoredDishaSession[]
): CounsellorSession[] {
  const merged = new Map<string, CounsellorSession>();

  for (const session of browserSessions) {
    merged.set(session.room, { ...session, source: 'browser', signupPhone: null });
  }
  for (const session of apiSessions) {
    const localSession = merged.get(session.room);
    const combinedEvents = localSession
      ? [...localSession.events, ...session.events]
      : session.events;
    const uniqueEvents = [
      ...new Map(
        combinedEvents.map((event) => [`${event.type}:${event.ts}:${JSON.stringify(event)}`, event])
      ).values(),
    ];
    merged.set(session.room, {
      ...session,
      events: uniqueEvents,
      updatedAt: Math.max(session.updatedAt, localSession?.updatedAt ?? 0),
      source: 'api',
    });
  }

  return [...merged.values()].sort((a, b) => b.updatedAt - a.updatedAt);
}

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

export function CounsellorView() {
  const [browserSessions, setBrowserSessions] = useState<StoredDishaSession[]>([]);
  const [apiSessions, setApiSessions] = useState<CounsellorSession[]>([]);
  const [apiState, setApiState] = useState<'loading' | 'ready' | 'unavailable'>('loading');

  useEffect(() => {
    const refreshBrowserSessions = () => setBrowserSessions(readAllStoredSessions());
    const handleStorage = (event: StorageEvent) => {
      if (event.key?.startsWith(DISHA_STORAGE_PREFIX)) refreshBrowserSessions();
    };

    refreshBrowserSessions();
    window.addEventListener('storage', handleStorage);
    const controller = new AbortController();

    fetchApiSessions(controller.signal)
      .then((sessions) => {
        setApiSessions(sessions);
        setApiState('ready');
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return;
        setApiState('unavailable');
      });

    return () => {
      controller.abort();
      window.removeEventListener('storage', handleStorage);
    };
  }, []);

  const sessions = useMemo(
    () => mergeSessions(apiSessions, browserSessions),
    [apiSessions, browserSessions]
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

        {apiState === 'unavailable' && (
          <div className="border-disha-sun/35 bg-disha-sun/10 mt-6 flex items-start gap-3 rounded-xl border p-3 text-sm">
            <DatabaseZap className="text-disha-leaf mt-0.5 size-4 shrink-0" />
            <p>
              Case API अभी उपलब्ध नहीं है।
              {browserSessions.length > 0
                ? ' इस browser में save हुए live sessions नीचे दिख रहे हैं।'
                : ' Live session के events इस browser में आते ही यहाँ दिखेंगे।'}
            </p>
          </div>
        )}

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
              <table className="w-full min-w-[860px] border-collapse text-left">
                <caption className="sr-only">
                  Disha sessions with signup phones, practical constraints, and counsellor review
                  notes
                </caption>
                <thead>
                  <tr className="bg-muted/70 text-muted-foreground text-xs tracking-wide uppercase">
                    <th className="px-5 py-3 font-semibold">Session</th>
                    <th className="px-5 py-3 font-semibold">Phone</th>
                    <th className="px-5 py-3 font-semibold">Constraints</th>
                    <th className="px-5 py-3 font-semibold">Review notes</th>
                    <th className="px-5 py-3 font-semibold">Updated</th>
                  </tr>
                </thead>
                <tbody className="divide-border/60 divide-y">
                  {sessions.map((session) => {
                    const snapshot = deriveDishaSnapshot(session.events);
                    const constraints = Object.values(snapshot.constraints);
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
