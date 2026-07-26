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

/** One pathway-tree node as the agent found it, with everything a student can
 *  go and read for themselves: where it leads, how long it takes, and the link. */
export interface CareerMatch {
  path: string;
  jobs: string;
  link: string;
  level?: string;
  duration?: string;
  eligibility?: string;
  note?: string;
  state?: string;
  children: string[];
}

export interface CareerEvent extends DishaEventBase {
  type: 'career';
  query: string;
  paths: string[];
  matches: CareerMatch[];
}

export interface ScholarshipScheme {
  name: string;
  provider: string;
  level: string;
  eligibility: string;
  source_url: string;
  amount?: string;
  income_ceiling?: string;
  state?: string;
}

export interface ScholarshipEvent extends DishaEventBase {
  type: 'scholarship';
  query: string;
  schemes: ScholarshipScheme[];
}

export interface KbCitation {
  source: string;
  page: number;
  citation: string;
  /** The passage the agent actually read, so the student can re-read it. */
  text?: string;
}

export interface KbEvent extends DishaEventBase {
  type: 'kb';
  query: string;
  citations: KbCitation[];
}

/** Who the student is, as the agent learned it in conversation. Later events
 *  carry the full accumulated profile, so the last one seen wins whole. */
export interface ProfileEvent extends DishaEventBase {
  type: 'profile';
  name?: string;
  class_level?: string;
  stream?: string;
  interests?: string[];
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
  | ScholarshipEvent
  | KbEvent
  | ProfileEvent
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
  careerMatches: CareerMatch[];
  scholarships: ScholarshipScheme[];
  citations: KbCitation[];
  flags: FlagEvent[];
  refusals: RefusalEvent[];
  strengths: DishaStrength[];
  profile?: ProfileEvent;
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

/** Copy a field only when the source actually carried a value. An empty
 *  string rendered as "Duration: " reads as missing data, not as absent data. */
function optionalString(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim().length > 0 ? value : undefined;
}

function parseCareerMatch(value: unknown): CareerMatch | null {
  if (!isRecord(value) || typeof value.path !== 'string' || value.path.length === 0) {
    return null;
  }

  return {
    path: value.path,
    jobs: typeof value.jobs === 'string' ? value.jobs : '',
    link: typeof value.link === 'string' ? value.link : '',
    level: optionalString(value.level),
    duration: optionalString(value.duration),
    eligibility: optionalString(value.eligibility),
    note: optionalString(value.note),
    state: optionalString(value.state),
    children: isStringArray(value.children) ? value.children : [],
  };
}

function parseScholarshipScheme(value: unknown): ScholarshipScheme | null {
  if (!isRecord(value) || typeof value.name !== 'string' || value.name.length === 0) {
    return null;
  }

  return {
    name: value.name,
    provider: typeof value.provider === 'string' ? value.provider : '',
    level: typeof value.level === 'string' ? value.level : '',
    eligibility: typeof value.eligibility === 'string' ? value.eligibility : '',
    source_url: typeof value.source_url === 'string' ? value.source_url : '',
    amount: optionalString(value.amount),
    income_ceiling: optionalString(value.income_ceiling),
    state: optionalString(value.state),
  };
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
    case 'career': {
      if (typeof value.query !== 'string' || !isStringArray(value.paths)) return null;
      // Sessions recorded before the agent sent full matches only have paths.
      // Reconstruct a bare match so the reading list still renders those rows.
      const matches = Array.isArray(value.matches)
        ? value.matches.map(parseCareerMatch).filter((match) => match !== null)
        : value.paths.map((path) => ({ path, jobs: '', link: '', children: [] }));
      return {
        type: 'career',
        ts: value.ts,
        query: value.query,
        paths: value.paths,
        matches,
      };
    }
    case 'scholarship': {
      if (typeof value.query !== 'string' || !Array.isArray(value.schemes)) return null;
      const schemes = value.schemes.map(parseScholarshipScheme).filter((scheme) => scheme !== null);
      return schemes.length > 0
        ? { type: 'scholarship', ts: value.ts, query: value.query, schemes }
        : null;
    }
    case 'kb':
      return typeof value.query === 'string' && isCitationArray(value.citations)
        ? {
            type: 'kb',
            ts: value.ts,
            query: value.query,
            citations: value.citations.map((citation) => ({
              source: citation.source,
              page: citation.page,
              citation: citation.citation,
              text: optionalString(citation.text),
            })),
          }
        : null;
    case 'profile': {
      const profile: ProfileEvent = {
        type: 'profile',
        ts: value.ts,
        name: optionalString(value.name),
        class_level: optionalString(value.class_level),
        stream: optionalString(value.stream),
        interests: isStringArray(value.interests) ? value.interests : undefined,
      };
      return profile.name || profile.class_level || profile.stream || profile.interests
        ? profile
        : null;
    }
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
    careerMatches: [],
    scholarships: [],
    citations: [],
    flags: [],
    refusals: [],
    strengths: [],
  };
  const seenPaths = new Set<string>();
  const seenCitations = new Set<string>();
  const seenStrengthLabels = new Set<string>();
  const matchByPath = new Map<string, CareerMatch>();
  const schemeByName = new Map<string, ScholarshipScheme>();

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
        for (const match of event.matches) {
          // A later lookup of the same node can carry detail an earlier one
          // lacked, so merge rather than keep whichever arrived first.
          const existing = matchByPath.get(match.path);
          matchByPath.set(match.path, existing ? { ...existing, ...match } : match);
        }
        break;
      case 'scholarship':
        for (const scheme of event.schemes) {
          if (!schemeByName.has(scheme.name)) schemeByName.set(scheme.name, scheme);
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
      case 'profile':
        // Each profile event carries the whole accumulated profile, so the
        // latest one replaces rather than merges.
        snapshot.profile = event;
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

  // Keep the order the conversation surfaced them in — that ordering is the
  // student's own priority, not an alphabetical one we invented.
  snapshot.careerMatches = snapshot.careerPaths
    .map((path) => matchByPath.get(path))
    .filter((match) => match !== undefined);
  snapshot.scholarships = [...schemeByName.values()];

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
