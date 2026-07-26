export const DISHA_TOPIC = 'disha';
export const DISHA_CLIENT_TOPIC = 'disha.client';
export const DISHA_STORAGE_PREFIX = 'disha:session:v1:';

export const CONSTRAINT_NAMES = [
  'distance_from_home',
  'hostel_needed',
  'fee_ceiling',
  'family_permission',
  'scholarship_dependence',
] as const;

export const FLAG_TYPES = ['distress', 'family_pressure', 'choice_paralysis', 'self_harm'] as const;

export type ConstraintName = (typeof CONSTRAINT_NAMES)[number];
export type DishaFlagType = (typeof FLAG_TYPES)[number];

interface DishaEventBase {
  ts: number;
}

export interface ConstraintEvent extends DishaEventBase {
  type: 'constraint';
  name: ConstraintName;
  value: string;
}

export interface FlagEvent extends DishaEventBase {
  type: 'flag';
  flag_type: DishaFlagType;
  quote: string;
}

export interface RefusalEvent extends DishaEventBase {
  type: 'refusal';
  asked_about: string;
}

export interface CareerEvent extends DishaEventBase {
  type: 'career';
  query: string;
  paths: string[];
}

export interface KbCitation {
  source: string;
  page: number;
  citation: string;
}

export interface KbEvent extends DishaEventBase {
  type: 'kb';
  query: string;
  citations: KbCitation[];
}

export interface SummaryEvent extends DishaEventBase {
  type: 'summary';
  summary_hi: string;
  shortlist: string[];
  next_steps: string[];
}

export interface DishaStrength {
  label: string;
  evidence_quote: string;
}

export interface StrengthEvent extends DishaEventBase {
  type: 'strength';
  strengths: DishaStrength[];
}

export interface TestResultEvent extends DishaEventBase {
  type: 'test_result';
  stream: string;
  fit_note: string;
  evidence: string[];
}

export type DishaEvent =
  | ConstraintEvent
  | FlagEvent
  | RefusalEvent
  | CareerEvent
  | KbEvent
  | SummaryEvent
  | StrengthEvent
  | TestResultEvent;

export interface StoredDishaSession {
  room: string;
  events: DishaEvent[];
  updatedAt: number;
}

export interface DishaSessionSnapshot {
  constraints: Partial<Record<ConstraintName, ConstraintEvent>>;
  careerPaths: string[];
  citations: KbCitation[];
  flags: FlagEvent[];
  refusals: RefusalEvent[];
  strengths: DishaStrength[];
  summary?: SummaryEvent;
  testResult?: TestResultEvent;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === 'string');
}

function isCitationArray(value: unknown): value is KbCitation[] {
  return (
    Array.isArray(value) &&
    value.every(
      (item) =>
        isRecord(item) &&
        typeof item.source === 'string' &&
        typeof item.page === 'number' &&
        typeof item.citation === 'string'
    )
  );
}

function isStrengthArray(value: unknown): value is DishaStrength[] {
  return (
    Array.isArray(value) &&
    value.length > 0 &&
    value.every(
      (item) =>
        isRecord(item) &&
        typeof item.label === 'string' &&
        item.label.trim().length > 0 &&
        typeof item.evidence_quote === 'string' &&
        item.evidence_quote.trim().length > 0
    )
  );
}

function isConstraintName(value: unknown): value is ConstraintName {
  return typeof value === 'string' && CONSTRAINT_NAMES.includes(value as ConstraintName);
}

function isFlagType(value: unknown): value is DishaFlagType {
  return typeof value === 'string' && FLAG_TYPES.includes(value as DishaFlagType);
}

export function parseDishaEvent(value: unknown): DishaEvent | null {
  if (!isRecord(value) || typeof value.type !== 'string' || typeof value.ts !== 'number') {
    return null;
  }

  if (!Number.isFinite(value.ts)) {
    return null;
  }

  switch (value.type) {
    case 'constraint':
      return isConstraintName(value.name) && typeof value.value === 'string'
        ? {
            type: 'constraint',
            ts: value.ts,
            name: value.name,
            value: value.value,
          }
        : null;
    case 'flag':
      return isFlagType(value.flag_type) && typeof value.quote === 'string'
        ? {
            type: 'flag',
            ts: value.ts,
            flag_type: value.flag_type,
            quote: value.quote,
          }
        : null;
    case 'refusal':
      return typeof value.asked_about === 'string'
        ? {
            type: 'refusal',
            ts: value.ts,
            asked_about: value.asked_about,
          }
        : null;
    case 'career':
      return typeof value.query === 'string' && isStringArray(value.paths)
        ? {
            type: 'career',
            ts: value.ts,
            query: value.query,
            paths: value.paths,
          }
        : null;
    case 'kb':
      return typeof value.query === 'string' && isCitationArray(value.citations)
        ? {
            type: 'kb',
            ts: value.ts,
            query: value.query,
            citations: value.citations,
          }
        : null;
    case 'summary':
      return typeof value.summary_hi === 'string' &&
        isStringArray(value.shortlist) &&
        isStringArray(value.next_steps)
        ? {
            type: 'summary',
            ts: value.ts,
            summary_hi: value.summary_hi,
            shortlist: value.shortlist,
            next_steps: value.next_steps,
          }
        : null;
    case 'strength':
      return isStrengthArray(value.strengths)
        ? {
            type: 'strength',
            ts: value.ts,
            strengths: value.strengths,
          }
        : null;
    case 'test_result':
      return typeof value.stream === 'string' &&
        typeof value.fit_note === 'string' &&
        isStringArray(value.evidence)
        ? {
            type: 'test_result',
            ts: value.ts,
            stream: value.stream,
            fit_note: value.fit_note,
            evidence: value.evidence,
          }
        : null;
    default:
      return null;
  }
}

export function decodeDishaPayload(payload: Uint8Array): DishaEvent | null {
  try {
    return parseDishaEvent(JSON.parse(new TextDecoder().decode(payload)));
  } catch {
    return null;
  }
}

export function deriveDishaSnapshot(events: DishaEvent[]): DishaSessionSnapshot {
  const snapshot: DishaSessionSnapshot = {
    constraints: {},
    careerPaths: [],
    citations: [],
    flags: [],
    refusals: [],
    strengths: [],
  };
  const seenPaths = new Set<string>();
  const seenCitations = new Set<string>();
  const seenStrengthLabels = new Set<string>();

  for (const event of events) {
    switch (event.type) {
      case 'constraint':
        snapshot.constraints[event.name] = event;
        break;
      case 'career':
        for (const path of event.paths) {
          if (!seenPaths.has(path)) {
            snapshot.careerPaths.push(path);
            seenPaths.add(path);
          }
        }
        break;
      case 'kb':
        for (const citation of event.citations) {
          if (!seenCitations.has(citation.citation)) {
            snapshot.citations.push(citation);
            seenCitations.add(citation.citation);
          }
        }
        break;
      case 'flag':
        snapshot.flags.push(event);
        break;
      case 'refusal':
        snapshot.refusals.push(event);
        break;
      case 'summary':
        snapshot.summary = event;
        break;
      case 'strength':
        for (const strength of event.strengths) {
          if (!seenStrengthLabels.has(strength.label)) {
            snapshot.strengths.push(strength);
            seenStrengthLabels.add(strength.label);
          }
        }
        break;
      case 'test_result':
        snapshot.testResult = event;
        break;
    }
  }

  return snapshot;
}

export function readStoredSession(room: string): StoredDishaSession | null {
  if (typeof window === 'undefined' || !room) return null;

  try {
    const parsed: unknown = JSON.parse(
      window.localStorage.getItem(`${DISHA_STORAGE_PREFIX}${room}`) ?? ''
    );
    if (!isRecord(parsed) || parsed.room !== room || !Array.isArray(parsed.events)) {
      return null;
    }

    const events = parsed.events.map(parseDishaEvent).filter((event) => event !== null);
    return {
      room,
      events,
      updatedAt:
        typeof parsed.updatedAt === 'number' && Number.isFinite(parsed.updatedAt)
          ? parsed.updatedAt
          : 0,
    };
  } catch {
    return null;
  }
}

export function readAllStoredSessions(): StoredDishaSession[] {
  if (typeof window === 'undefined') return [];

  const sessions: StoredDishaSession[] = [];
  for (let index = 0; index < window.localStorage.length; index += 1) {
    const key = window.localStorage.key(index);
    if (!key?.startsWith(DISHA_STORAGE_PREFIX)) continue;

    const room = key.slice(DISHA_STORAGE_PREFIX.length);
    const session = readStoredSession(room);
    if (session) sessions.push(session);
  }

  return sessions.sort((a, b) => b.updatedAt - a.updatedAt);
}

export function writeStoredSession(room: string, events: DishaEvent[]): void {
  if (typeof window === 'undefined' || !room || events.length === 0) return;

  const session: StoredDishaSession = {
    room,
    events,
    updatedAt: Date.now(),
  };

  try {
    window.localStorage.setItem(`${DISHA_STORAGE_PREFIX}${room}`, JSON.stringify(session));
  } catch {
    // Storage may be unavailable in private browsing or a restricted iframe.
  }
}
