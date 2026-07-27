import { unstable_cache } from 'next/cache';
import type { DishaSessionSnapshot } from '@/lib/disha-events';

// SERVER-ONLY module. It reads process.env.OPENAI_API_KEY and calls OpenAI.
// It must never be imported into a client component — only the /me server
// component imports it, and only the already-grounded result (never the key,
// never the raw prompt) is handed to the client. There is no 'use client'
// here and every export depends on next/cache, which throws in the browser.

const OPENAI_URL = 'https://api.openai.com/v1/chat/completions';
const OPENAI_MODEL = 'gpt-4.1-mini';
const REQUEST_TIMEOUT_MS = 25_000;
const MAX_PATHS = 3;

/** One recommended path in the guide. Its `link` and `duration` are copied
 *  from the student's own careerMatches snapshot, never from the model — the
 *  model may only choose WHICH known path to talk about, not invent its URL. */
export interface GuidePath {
  path: string;
  crumb: string;
  heading: string;
  why: string;
  nextStep: string;
  link: string;
  duration?: string;
}

/** A free way to start, drawn only from opportunities already in the snapshot.
 *  `url`, `what` and `cost` come from the snapshot; only `why` is model prose. */
export interface GuideFreeStart {
  name: string;
  provider: string;
  what: string;
  cost: string;
  url: string;
  why: string;
}

export interface DishaGuide {
  ok: true;
  whoYouAre: string;
  paths: GuidePath[];
  freeStarts: GuideFreeStart[];
  close: string;
}

export interface GuideFallback {
  ok: false;
  reason: 'no-summary' | 'no-key' | 'error';
  summaryHi?: string;
  nextSteps?: string[];
}

export type GuideResult = DishaGuide | GuideFallback;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function asString(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

/** Strip any markdown link whose destination is not in the allow-list, keeping
 *  the visible text. Grounding defence: even if the model writes a link inside
 *  its prose, only URLs the student was actually shown survive. */
function sanitizeLinks(markdown: string, allowedUrls: Set<string>): string {
  if (!markdown) return '';
  return markdown.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_match, text: string, url: string) =>
    allowedUrls.has(url.trim()) ? `[${text}](${url.trim()})` : text
  );
}

function pathCrumb(path: string): { crumb: string; heading: string } {
  const parts = path.split(' > ');
  return {
    crumb: parts.slice(0, -1).join(' › '),
    heading: parts[parts.length - 1] ?? path,
  };
}

/** Build the model input from ONLY the grounded, student-specific facts. No
 *  free text is invented here; the model is handed exactly what it may speak
 *  about and is told, in the system prompt, that it may speak about nothing else. */
function buildPrompt(snapshot: DishaSessionSnapshot) {
  const profile = snapshot.profile;
  const careerMatches = snapshot.careerMatches.map((match) => ({
    path: match.path,
    duration: match.duration ?? null,
    jobs: match.jobs || null,
    link: match.link || null,
  }));

  const student = {
    name: profile?.name ?? null,
    class_level: profile?.class_level ?? null,
    stream: profile?.stream ?? null,
    interests: profile?.interests ?? [],
    constraints: Object.fromEntries(
      Object.entries(snapshot.constraints).map(([name, event]) => [name, event?.value ?? ''])
    ),
    decisions: snapshot.decisions.map((decision) => decision.decision),
    strengths: snapshot.strengths.map((strength) => strength.label),
    test_result: snapshot.testResult
      ? { stream: snapshot.testResult.stream, fit_note: snapshot.testResult.fit_note }
      : null,
    summary_hi: snapshot.summary?.summary_hi ?? '',
    next_steps: snapshot.summary?.next_steps ?? [],
    // The ONLY careers the guide may mention. Copy path strings verbatim.
    career_matches: careerMatches,
    // The ONLY free programmes the guide may mention.
    opportunities: snapshot.opportunities.map((opportunity) => ({
      name: opportunity.name,
      provider: opportunity.provider,
      what: opportunity.what,
      cost: opportunity.cost,
    })),
  };

  const system = [
    'You are Disha, a warm, honest Indian career counsellor writing a short personal guide for one student.',
    'Write in simple, Hindi-leaning language (Devanagari with common English words the student already uses, like "stream", "diploma", "college"). Warm, plain, encouraging — never salesy.',
    '',
    'GROUNDING RULES (absolute, non-negotiable):',
    '- You may ONLY name careers, courses or paths that appear in career_matches. Copy each `path` string VERBATIM into paths[].path. Never invent a career, college, exam, or path that is not in that list.',
    '- You may ONLY name free programmes that appear in opportunities, and only in free_starts.',
    '- NEVER invent or state any fee, salary, cutoff, package, scholarship amount, ranking, or admission date. If you do not have a number from the student data, do not give a number.',
    '- Do not write any URLs or markdown links yourself. Links are attached by the system afterwards.',
    "- Ground every claim in the student's own constraints, interests, strengths, decisions and test result.",
    '',
    'Return ONLY a JSON object with this exact shape:',
    '{',
    '  "who_you_are": string,            // one short markdown paragraph, second person ("आप")',
    '  "paths": [                        // 2 to 3 items, each a real path from career_matches',
    '    { "path": string,               // verbatim from career_matches',
    '      "why": string,                // 1-2 sentences: why it fits THIS student\'s constraints/interests',
    '      "next_step": string }         // one honest, concrete next step the student can take',
    '  ],',
    '  "free_starts": [                  // 0 or more, ONLY from opportunities; [] if none provided',
    '    { "name": string, "why": string } ],',
    '  "close": string                  // one short encouraging markdown paragraph',
    '}',
  ].join('\n');

  const user = `Student data (this is everything you may use):\n${JSON.stringify(student, null, 2)}`;

  return { system, user };
}

/** Calls OpenAI, then re-grounds the response against the snapshot in code:
 *  path strings and links are taken from the snapshot, unknown paths/opps are
 *  dropped, and stray links in prose are stripped. THROWS on any failure so a
 *  transient error is never cached — the next visit retries. */
async function generateGuide(snapshot: DishaSessionSnapshot): Promise<DishaGuide> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) throw new Error('OPENAI_API_KEY missing');

  const { system, user } = buildPrompt(snapshot);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let raw: string;
  try {
    const response = await fetch(OPENAI_URL, {
      method: 'POST',
      signal: controller.signal,
      headers: {
        'content-type': 'application/json',
        authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: OPENAI_MODEL,
        temperature: 0.4,
        max_tokens: 1200,
        response_format: { type: 'json_object' },
        messages: [
          { role: 'system', content: system },
          { role: 'user', content: user },
        ],
      }),
    });

    if (!response.ok) {
      throw new Error(`OpenAI ${response.status}`);
    }
    const payload: unknown = await response.json();
    const content =
      isRecord(payload) &&
      Array.isArray(payload.choices) &&
      isRecord(payload.choices[0]) &&
      isRecord(payload.choices[0].message)
        ? payload.choices[0].message.content
        : undefined;
    if (typeof content !== 'string' || content.trim().length === 0) {
      throw new Error('OpenAI empty content');
    }
    raw = content;
  } finally {
    clearTimeout(timeout);
  }

  const parsed: unknown = JSON.parse(raw);
  if (!isRecord(parsed)) throw new Error('OpenAI non-object JSON');

  // Re-ground: build the allow-lists from the snapshot itself.
  const matchByPath = new Map(snapshot.careerMatches.map((match) => [match.path, match]));
  const opportunityByName = new Map(
    snapshot.opportunities.map((opportunity) => [opportunity.name, opportunity])
  );
  const allowedUrls = new Set<string>();
  for (const match of snapshot.careerMatches) if (match.link) allowedUrls.add(match.link);
  for (const opportunity of snapshot.opportunities) {
    if (opportunity.source_url) allowedUrls.add(opportunity.source_url);
  }

  const rawPaths = Array.isArray(parsed.paths) ? parsed.paths : [];
  const seenPaths = new Set<string>();
  const paths: GuidePath[] = [];
  for (const item of rawPaths) {
    if (paths.length >= MAX_PATHS) break;
    if (!isRecord(item)) continue;
    const path = asString(item.path);
    const match = matchByPath.get(path);
    if (!match || seenPaths.has(path)) continue; // unknown path invented → drop
    seenPaths.add(path);
    const { crumb, heading } = pathCrumb(path);
    paths.push({
      path,
      crumb,
      heading,
      why: sanitizeLinks(asString(item.why), allowedUrls),
      nextStep: sanitizeLinks(asString(item.next_step), allowedUrls),
      link: match.link, // from snapshot, never the model
      duration: match.duration,
    });
  }

  const rawFreeStarts = Array.isArray(parsed.free_starts) ? parsed.free_starts : [];
  const seenOpps = new Set<string>();
  const freeStarts: GuideFreeStart[] = [];
  for (const item of rawFreeStarts) {
    if (!isRecord(item)) continue;
    const name = asString(item.name);
    const opportunity = opportunityByName.get(name);
    if (!opportunity || seenOpps.has(name)) continue; // unknown opp → drop
    seenOpps.add(name);
    freeStarts.push({
      name: opportunity.name,
      provider: opportunity.provider,
      what: opportunity.what,
      cost: opportunity.cost,
      url: opportunity.source_url, // from snapshot
      why: sanitizeLinks(asString(item.why), allowedUrls),
    });
  }

  // If the model gave us no usable grounded path, fall back rather than ship an
  // empty document — caught by getDishaGuide and rendered as summary + steps.
  if (paths.length === 0) throw new Error('no grounded path in model output');

  return {
    ok: true,
    whoYouAre: sanitizeLinks(asString(parsed.who_you_are), allowedUrls),
    paths,
    freeStarts,
    close: sanitizeLinks(asString(parsed.close), allowedUrls),
  };
}

/**
 * Return the student's guide, generating it once and caching it. The cache key
 * is (phone/case + the summary's timestamp): the guide only regenerates when a
 * NEWER call has ended and produced a fresh summary, not on every page visit.
 * The snapshot is captured in the closure, NOT passed as a cached argument, so
 * changes to unrelated parts of the snapshot (utterances, etc.) do not bust it.
 */
export async function getDishaGuide(
  phone: string,
  snapshot: DishaSessionSnapshot
): Promise<GuideResult> {
  const summary = snapshot.summary;
  if (!summary) return { ok: false, reason: 'no-summary' };

  const fallback: GuideFallback = {
    ok: false,
    reason: 'error',
    summaryHi: summary.summary_hi,
    nextSteps: summary.next_steps,
  };

  if (!process.env.OPENAI_API_KEY) {
    return { ...fallback, reason: 'no-key' };
  }

  const cacheKey = `${phone || 'anon'}:${summary.ts}`;
  const loadGuide = unstable_cache(() => generateGuide(snapshot), ['disha-guide', cacheKey], {
    revalidate: false,
    tags: ['disha-guide', `disha-guide:${phone}`],
  });

  try {
    return await loadGuide();
  } catch {
    // A throw here is never cached by unstable_cache, so the next visit retries.
    return fallback;
  }
}
