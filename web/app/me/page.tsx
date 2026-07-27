import type { Metadata } from 'next';
import { cookies } from 'next/headers';
import Link from 'next/link';
import { DishaBrand } from '@/components/disha/disha-brand';
import { LoginCard } from '@/components/disha/login-card';
import { MeTabs } from '@/components/disha/me-tabs';
import {
  type DishaSessionSnapshot,
  deriveDishaSnapshot,
  parseDishaEvent,
} from '@/lib/disha-events';
import { getDishaGuide } from '@/lib/disha-guide';

export const metadata: Metadata = {
  title: 'मेरी प्रोफ़ाइल — Disha',
  description: 'Disha से हुई बातचीत में बनी आपकी profile — strengths, रास्ते और अगले कदम।',
};

// The profile is rebuilt from the case file on every visit — a call may have
// just ended, and a cached page would hide exactly that call.
export const dynamic = 'force-dynamic';

const API_ORIGIN = process.env.DISHA_API_ORIGIN ?? 'http://sarvam-api:8090';

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

export default async function MePage() {
  const me = await fetchMe();
  // Generate the guide server-side so the OpenAI key never reaches the client.
  // getDishaGuide caches on (phone + summary.ts), so this is a cache hit on
  // every visit until a newer call ends.
  const guide = me ? await getDishaGuide(me.phone, me.snapshot) : null;

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
          <MeTabs phone={me.phone} snapshot={me.snapshot} guide={guide!} />
        )}
      </div>
    </main>
  );
}
