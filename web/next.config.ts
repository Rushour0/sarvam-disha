import type { NextConfig } from 'next';

const BLOG_ORIGIN = process.env.BLOG_ORIGIN ?? 'https://sarvam-blog.pages.dev';
// Compose service name; resolvable only inside the deployment network.
const DISHA_API_ORIGIN = process.env.DISHA_API_ORIGIN ?? 'http://sarvam-api:8090';

const nextConfig: NextConfig = {
  // Build a self-contained server bundle so the runtime image does not need
  // node_modules.
  output: 'standalone',

  // Serve the blog under the product's own domain instead of a separate
  // pages.dev address. It stays its own Cloudflare Pages project with its own
  // CI — this only borrows the path, so a blog deploy never touches the app
  // and an app deploy never rebuilds the blog.
  //
  // The blog references its assets relatively ("./styles.css"), which is what
  // lets it be served from a subpath without rewriting its HTML.
  async rewrites() {
    return [
      { source: '/blog', destination: BLOG_ORIGIN },
      { source: '/blog/:path*', destination: `${BLOG_ORIGIN}/:path*` },

      // Proxy the case API through this server so it needs no public domain of
      // its own. It serves phone numbers and verbatim wellbeing quotes on
      // /cases, so the fewer ways to reach it the better — the browser talks
      // to this origin, and only this container talks to the API.
      { source: '/api/disha/:path*', destination: `${DISHA_API_ORIGIN}/:path*` },
    ];
  },
};

export default nextConfig;
