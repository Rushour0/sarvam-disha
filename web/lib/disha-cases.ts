/**
 * Normalising the case API's rows into the shape the counsellor screen renders.
 *
 * These helpers are deliberately free of React and of `window`: the counsellor
 * page fetches the case API on the server, so the API host never has to be
 * reachable from a student's browser. The same functions then run in the client
 * component when it merges browser-local sessions in.
 */
import { type DishaEvent, type StoredDishaSession, parseDishaEvent } from '@/lib/disha-events';

export interface CounsellorSession extends StoredDishaSession {
  source: 'api' | 'browser';
  signupPhone: string | null;
}

export type CaseApiState = 'ready' | 'unavailable' | 'not-configured';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function extractRoom(value: unknown): string {
  if (typeof value === 'string') return value;
  if (!isRecord(value)) return '';

  for (const key of ['room', 'room_name', 'id', 'name']) {
    if (typeof value[key] === 'string') return value[key];
  }
  return '';
}

export function timestampToMilliseconds(value: unknown): number {
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

export function normaliseApiSession(
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

/**
 * Read every case from the API. Server-only: `DISHA_API_URL` is not a
 * NEXT_PUBLIC_ variable, so calling this from a client component yields
 * 'not-configured' rather than leaking the host into the bundle.
 */
export async function fetchCounsellorSessions(): Promise<{
  sessions: CounsellorSession[];
  state: CaseApiState;
}> {
  const configuredBase = process.env.DISHA_API_URL?.trim();
  if (!configuredBase) return { sessions: [], state: 'not-configured' };

  const base = configuredBase.replace(/\/+$/, '');
  try {
    const casesResponse = await fetch(`${base}/cases`, { cache: 'no-store' });
    if (!casesResponse.ok) return { sessions: [], state: 'unavailable' };

    const caseList = extractCaseList(await casesResponse.json());
    const sessions = await Promise.all(
      caseList.map(async (caseEntry) => {
        const room = extractRoom(caseEntry);
        if (!room) return null;
        const signupPhone = extractSignupPhone(caseEntry);
        const updatedAt = timestampToMilliseconds(
          isRecord(caseEntry)
            ? (caseEntry.updated_at ?? caseEntry.updatedAt ?? caseEntry.updated ?? caseEntry.ts)
            : 0
        );

        try {
          const detailResponse = await fetch(`${base}/cases/${encodeURIComponent(room)}`, {
            cache: 'no-store',
          });
          if (detailResponse.ok) {
            return normaliseApiSession(await detailResponse.json(), room, signupPhone, updatedAt);
          }
        } catch {
          // Fall through to the list row, which still carries constraints and flags.
        }

        return normaliseApiSession(caseEntry, room, signupPhone, updatedAt);
      })
    );

    return { sessions: sessions.filter((session) => session !== null), state: 'ready' };
  } catch {
    return { sessions: [], state: 'unavailable' };
  }
}

export function mergeSessions(
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
