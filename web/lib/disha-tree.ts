/**
 * Server-side access to the pathway tree and scholarship list the agent
 * counsels from. Fetched from the internal case API (which reads the same
 * data/ files the agent loads), so the browse pages can never drift from what
 * Disha actually says on a call.
 */

export interface PathwayNode {
  id: string;
  parent_id: string | null;
  name: string;
  path: string;
  depth: number;
  kind: string;
  level: string | null;
  duration: string | null;
  eligibility: string | null;
  note: string | null;
  state: string | null;
  jobs: string[];
  scholarship_tags: string[];
  children: string[];
  link: string | null;
}

export interface PathwayTree {
  nodes: PathwayNode[];
  byId: Map<string, PathwayNode>;
  roots: PathwayNode[];
}

export interface TreeScholarship {
  id: string;
  name: string;
  provider: string;
  level: string;
  eligibility: string;
  source_url: string;
  amount?: string;
  income_ceiling?: string;
  state?: string;
  applies_to: string[];
}

const API_ORIGIN = process.env.DISHA_API_ORIGIN ?? 'http://sarvam-api:8090';

// The tree only changes on deploy, so an hour of staleness is fine and keeps
// every /explore render from re-downloading a 250 KB file from the API.
const REVALIDATE_SECONDS = 3600;

export async function fetchPathwayTree(): Promise<PathwayTree | null> {
  try {
    const response = await fetch(`${API_ORIGIN}/tree`, {
      next: { revalidate: REVALIDATE_SECONDS },
    });
    if (!response.ok) return null;

    const data: unknown = await response.json();
    if (typeof data !== 'object' || data === null) return null;
    const nodes = (data as { nodes?: unknown }).nodes;
    if (!Array.isArray(nodes)) return null;

    const typed = nodes as PathwayNode[];
    return {
      nodes: typed,
      byId: new Map(typed.map((node) => [node.id, node])),
      roots: typed.filter((node) => node.parent_id === null),
    };
  } catch {
    return null;
  }
}

export async function fetchScholarships(): Promise<TreeScholarship[]> {
  try {
    const response = await fetch(`${API_ORIGIN}/scholarships`, {
      next: { revalidate: REVALIDATE_SECONDS },
    });
    if (!response.ok) return [];

    const data: unknown = await response.json();
    return Array.isArray(data) ? (data as TreeScholarship[]) : [];
  } catch {
    return [];
  }
}

/** Schemes whose applies_to overlaps the node's tags — the same rule the
 *  agent's scholarships_for_tags uses, so page and voice never disagree. */
export function scholarshipsForTags(
  schemes: TreeScholarship[],
  tags: string[],
  limit = 4
): TreeScholarship[] {
  const wanted = new Set(tags);
  if (wanted.size === 0) return [];
  return schemes
    .filter((scheme) => scheme.applies_to?.some((tag) => wanted.has(tag)))
    .sort((a, b) => Number(!a.amount) - Number(!b.amount) || a.name.localeCompare(b.name))
    .slice(0, limit);
}
