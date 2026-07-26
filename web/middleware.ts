import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Basic auth on the counsellor surface.
 *
 * `/cases` returns every student's phone number and the verbatim quotes that
 * triggered a wellbeing flag. Those are the most sensitive rows this product
 * holds, and until there is real auth they must not be one URL away from
 * anyone who finds the domain.
 *
 * Set DISHA_COUNSELLOR_PASSWORD to enable. If it is unset the routes are
 * blocked outright rather than left open — a missing secret should fail closed.
 */

// NOTE: /counsellor is intentionally left open (no auth) per an explicit
// operator decision. The rendered page shows student phone numbers and
// verbatim wellbeing quotes, so anyone with the URL can read them. The raw
// bulk-cases path stays gated as defence in depth.
const PROTECTED = ['/api/disha/cases'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (!PROTECTED.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`))) {
    return NextResponse.next();
  }

  const password = process.env.DISHA_COUNSELLOR_PASSWORD;
  if (!password) {
    return new NextResponse('Counsellor access is not configured.', { status: 503 });
  }

  const header = request.headers.get('authorization') ?? '';
  if (header.startsWith('Basic ')) {
    const [user, given] = atob(header.slice(6)).split(':');
    // Compare full length both ways so a wrong password cannot be probed by
    // how quickly it is rejected.
    if (user === (process.env.DISHA_COUNSELLOR_USER ?? 'counsellor') && safeEqual(given, password)) {
      return NextResponse.next();
    }
  }

  return new NextResponse('Authentication required.', {
    status: 401,
    headers: { 'WWW-Authenticate': 'Basic realm="Disha counsellor", charset="UTF-8"' },
  });
}

function safeEqual(a: string | undefined, b: string): boolean {
  if (a === undefined || a.length !== b.length) return false;
  let diff = 0;
  for (let index = 0; index < b.length; index += 1) {
    diff |= a.charCodeAt(index) ^ b.charCodeAt(index);
  }
  return diff === 0;
}

export const config = {
  matcher: ['/api/disha/cases/:path*', '/api/disha/cases'],
};
