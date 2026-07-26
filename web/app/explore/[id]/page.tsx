import { cookies } from 'next/headers';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { ArrowRight, BriefcaseBusiness, ExternalLink, GraduationCap, Lock } from 'lucide-react';
import { DishaBrand } from '@/components/disha/disha-brand';
import { LoginCard } from '@/components/disha/login-card';
import {
  type PathwayNode,
  type PathwayTree,
  fetchPathwayTree,
  fetchScholarships,
  scholarshipsForTags,
} from '@/lib/disha-tree';

// Reads the session cookie, so this page is always request-rendered anyway.
export const dynamic = 'force-dynamic';

interface ExploreNodePageProps {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: ExploreNodePageProps) {
  const { id } = await params;
  const tree = await fetchPathwayTree();
  const node = tree?.byId.get(id);
  return {
    title: node ? `${node.name} — Disha career index` : 'Career index — Disha',
  };
}

function breadcrumb(tree: PathwayTree, node: PathwayNode): PathwayNode[] {
  const trail: PathwayNode[] = [];
  let current: PathwayNode | undefined = node;
  while (current) {
    trail.unshift(current);
    current = current.parent_id ? tree.byId.get(current.parent_id) : undefined;
  }
  return trail;
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2 text-sm leading-6">
      <dt className="text-muted-foreground shrink-0">{label}</dt>
      <dd className="font-medium">{value}</dd>
    </div>
  );
}

export default async function ExploreNodePage({ params }: ExploreNodePageProps) {
  const { id } = await params;
  const tree = await fetchPathwayTree();
  if (!tree) {
    return (
      <main className="bg-disha-wash min-h-svh">
        <div className="mx-auto w-full max-w-3xl px-4 py-6 sm:px-6 md:py-10">
          <DishaBrand />
          <p className="border-border/70 bg-card text-muted-foreground mt-8 rounded-[1.5rem] border border-dashed p-6 text-sm leading-6">
            Career index अभी load नहीं हो पाया। थोड़ी देर बाद फिर कोशिश करें।
          </p>
        </div>
      </main>
    );
  }

  const node = tree.byId.get(id);
  if (!node) notFound();

  const trail = breadcrumb(tree, node);
  const childNodes = node.children
    .map((childId) => tree.byId.get(childId))
    .filter((child) => child !== undefined);

  // Soft gate: the path itself is free to read; the official link and the
  // matched scholarship money-detail unlock with the phone login, same as the
  // post-call reference list.
  const unlocked = (await cookies()).has('disha_session');
  const schemes = unlocked
    ? scholarshipsForTags(await fetchScholarships(), node.scholarship_tags)
    : [];

  return (
    <main className="bg-disha-wash min-h-svh">
      <div className="mx-auto w-full max-w-3xl px-4 py-6 sm:px-6 md:py-10">
        <div className="flex items-center justify-between">
          <DishaBrand />
          <Link
            href="/"
            className="text-disha-leaf focus-visible:ring-ring min-h-11 rounded-full px-3 py-3 text-sm font-medium underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:outline-none"
          >
            Disha से बात करें
          </Link>
        </div>

        <nav aria-label="Breadcrumb" className="text-muted-foreground mt-8 text-xs leading-5">
          <ol className="flex flex-wrap items-center gap-1">
            <li>
              <Link href="/explore" className="hover:text-foreground hover:underline">
                Career index
              </Link>
            </li>
            {trail.map((ancestor, index) => (
              <li key={ancestor.id} className="flex items-center gap-1">
                <span aria-hidden="true">›</span>
                {index < trail.length - 1 ? (
                  <Link
                    href={`/explore/${ancestor.id}`}
                    className="hover:text-foreground hover:underline"
                  >
                    {ancestor.name}
                  </Link>
                ) : (
                  <span aria-current="page" className="text-foreground font-medium">
                    {ancestor.name}
                  </span>
                )}
              </li>
            ))}
          </ol>
        </nav>

        <article className="border-border/70 bg-card mt-4 rounded-[2rem] border p-5 sm:p-7">
          <h1 className="text-2xl font-semibold tracking-tight text-balance sm:text-3xl">
            {node.name}
          </h1>

          <dl className="mt-4 space-y-1">
            {node.level && <DetailRow label="स्तर:" value={node.level} />}
            {node.duration && <DetailRow label="अवधि:" value={node.duration} />}
            {node.eligibility && <DetailRow label="Eligibility:" value={node.eligibility} />}
            {node.state && <DetailRow label="राज्य:" value={node.state} />}
          </dl>

          {node.note && <p className="text-muted-foreground mt-3 text-sm leading-6">{node.note}</p>}

          {node.jobs.length > 0 && (
            <div className="mt-5">
              <h2 className="flex items-center gap-2 text-xs font-bold tracking-[0.12em] uppercase">
                <BriefcaseBusiness className="text-disha-sun size-4" aria-hidden="true" />
                इस रास्ते से मिलने वाले काम
              </h2>
              <ul className="mt-2 flex flex-wrap gap-1.5">
                {node.jobs.map((job) => (
                  <li
                    key={job}
                    className="bg-disha-sun/12 rounded-full px-2.5 py-1 text-xs leading-4"
                  >
                    {job}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {node.link &&
            (unlocked ? (
              <a
                href={node.link}
                target="_blank"
                rel="noreferrer noopener"
                className="text-disha-leaf focus-visible:ring-ring mt-5 inline-flex min-h-11 items-center gap-1.5 text-sm font-semibold underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:outline-none"
              >
                आधिकारिक जानकारी पढ़ें
                <ExternalLink className="size-3.5" aria-hidden="true" />
              </a>
            ) : (
              <p className="text-muted-foreground mt-5 flex items-center gap-1.5 text-sm">
                <Lock className="size-3.5" aria-hidden="true" />
                आधिकारिक link login के बाद खुलता है।
              </p>
            ))}
        </article>

        {childNodes.length > 0 && (
          <section className="mt-4">
            <h2 className="px-1 text-xs font-bold tracking-[0.12em] uppercase">आगे के रास्ते</h2>
            <ul className="mt-2 grid gap-2 sm:grid-cols-2">
              {childNodes.map((child) => (
                <li key={child.id}>
                  <Link
                    href={`/explore/${child.id}`}
                    className="border-border/70 bg-card hover:border-disha-leaf/50 focus-visible:ring-ring flex items-center justify-between gap-2 rounded-xl border p-3 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:outline-none"
                  >
                    {child.name}
                    <ArrowRight className="text-disha-leaf size-4 shrink-0" aria-hidden="true" />
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        )}

        {unlocked && schemes.length > 0 && (
          <section className="mt-4">
            <h2 className="flex items-center gap-2 px-1 text-xs font-bold tracking-[0.12em] uppercase">
              <GraduationCap className="text-disha-leaf size-4" aria-hidden="true" />
              इस रास्ते के लिए scholarships
            </h2>
            <ul className="mt-2 grid gap-3 sm:grid-cols-2">
              {schemes.map((scheme) => (
                <li
                  key={scheme.id}
                  className="border-disha-leaf/25 bg-disha-leaf/7 rounded-[1.25rem] border p-4"
                >
                  <h3 className="text-sm leading-6 font-semibold">{scheme.name}</h3>
                  <p className="text-muted-foreground mt-0.5 text-xs leading-5">
                    {scheme.provider}
                  </p>
                  <dl className="mt-2 space-y-1">
                    {scheme.amount && <DetailRow label="राशि:" value={scheme.amount} />}
                    {scheme.income_ceiling && (
                      <DetailRow label="आय सीमा:" value={scheme.income_ceiling} />
                    )}
                  </dl>
                  {scheme.source_url && (
                    <a
                      href={scheme.source_url}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="text-disha-leaf mt-2 inline-flex items-center gap-1.5 text-xs font-semibold underline-offset-4 hover:underline"
                    >
                      आधिकारिक page
                      <ExternalLink className="size-3" aria-hidden="true" />
                    </a>
                  )}
                </li>
              ))}
            </ul>
          </section>
        )}

        {!unlocked && (
          <div className="mt-4">
            <LoginCard
              title="पूरी जानकारी के लिए login करें"
              body="आधिकारिक links और इस रास्ते की scholarships मोबाइल नंबर से login करने पर खुलती हैं।"
            />
          </div>
        )}
      </div>
    </main>
  );
}
