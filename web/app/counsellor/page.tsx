import type { Metadata } from 'next';
import { CounsellorView } from '@/components/disha/counsellor-view';
import { fetchCounsellorSessions } from '@/lib/disha-cases';

export const metadata: Metadata = {
  title: 'Counsellor view — Disha',
  description: 'Disha session constraints and wellbeing notes for counsellor review.',
};

// Cases change with every call; a cached counsellor screen would hide the
// session that just ended, which is exactly the one a counsellor opens for.
export const dynamic = 'force-dynamic';

export default async function CounsellorPage() {
  const { sessions, state } = await fetchCounsellorSessions();
  return <CounsellorView initialSessions={sessions} apiState={state} />;
}
