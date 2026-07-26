import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowRight, Compass } from 'lucide-react';
import { DishaBrand } from '@/components/disha/disha-brand';
import { fetchPathwayTree } from '@/lib/disha-tree';

export const metadata: Metadata = {
  title: 'Career index — Disha',
  description:
    '10वीं-12वीं के बाद के सारे रास्ते एक जगह — degree, diploma, ITI, defence और scholarships के साथ।',
};

// The tree lives behind the internal API, which is unreachable at build time —
// render on request and let fetch-level revalidation do the caching.
export const dynamic = 'force-dynamic';

export default async function ExplorePage() {
  const tree = await fetchPathwayTree();

  return (
    <main className="bg-disha-wash min-h-svh">
      <div className="mx-auto w-full max-w-4xl px-4 py-6 sm:px-6 md:py-10">
        <div className="flex items-center justify-between">
          <DishaBrand />
          <Link
            href="/"
            className="text-disha-leaf focus-visible:ring-ring min-h-11 rounded-full px-3 py-3 text-sm font-medium underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:outline-none"
          >
            Disha से बात करें
          </Link>
        </div>

        <header className="mt-8 max-w-2xl">
          <div className="bg-disha-leaf/10 text-disha-leaf inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-semibold">
            <Compass className="size-4" aria-hidden="true" />
            Career index
          </div>
          <h1 className="mt-4 text-2xl font-semibold tracking-tight text-balance sm:text-3xl">
            10वीं-12वीं के बाद के सारे रास्ते, एक जगह
          </h1>
          <p className="text-muted-foreground mt-3 text-sm leading-6">
            यही वह सूची है जिससे Disha बातचीत में रास्ते सुझाती है — हर रास्ते के साथ अवधि,
            eligibility और आधिकारिक source। किसी stream से शुरू करें।
          </p>
        </header>

        {!tree ? (
          <p className="border-border/70 bg-card text-muted-foreground mt-8 rounded-[1.5rem] border border-dashed p-6 text-sm leading-6">
            Career index अभी load नहीं हो पाया। थोड़ी देर बाद फिर कोशिश करें।
          </p>
        ) : (
          <ul className="mt-8 grid gap-3 sm:grid-cols-2">
            {tree.roots.map((root) => (
              <li key={root.id}>
                <Link
                  href={`/explore/${root.id}`}
                  className="border-border/70 bg-card hover:border-disha-leaf/50 focus-visible:ring-ring block rounded-[1.5rem] border p-5 transition-colors focus-visible:ring-2 focus-visible:outline-none"
                >
                  <h2 className="flex items-center justify-between font-semibold">
                    {root.name}
                    <ArrowRight className="text-disha-leaf size-4 shrink-0" aria-hidden="true" />
                  </h2>
                  <p className="text-muted-foreground mt-1 text-sm">
                    {root.children.length} रास्ते
                  </p>
                  <ul className="mt-3 flex flex-wrap gap-1.5">
                    {root.children.slice(0, 4).map((childId) => {
                      const child = tree.byId.get(childId);
                      return child ? (
                        <li
                          key={childId}
                          className="bg-disha-sun/12 rounded-full px-2.5 py-1 text-xs leading-4"
                        >
                          {child.name}
                        </li>
                      ) : null;
                    })}
                    {root.children.length > 4 && (
                      <li className="text-muted-foreground px-1 py-1 text-xs leading-4">
                        +{root.children.length - 4} और
                      </li>
                    )}
                  </ul>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}
