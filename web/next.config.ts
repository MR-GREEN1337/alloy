import dns from 'dns';

// Fix for Node.js 18+ DNS resolution issues in Docker/certain environments
dns.setDefaultResultOrder('ipv4first');

// Get the backend URL from the environment.
const rawBackendUrl = process.env.NEXT_PUBLIC_API_URL;

// Throw a clear error during the build if the variable is not set.
if (!rawBackendUrl) {
  console.error("ERROR: The NEXT_PUBLIC_API_URL environment variable is not defined.");
  console.error("This is required for the Next.js rewrite proxy to function. Pass it as a --build-arg in your `docker build` command.");
  process.exit(1);
}

// --- THE FIX: NORMALIZE THE URL ---
// This ensures that even if the environment variable contains a path
// (e.g., https://.../api/v1), we only use the base origin for the proxy.
const backendApiOrigin = new URL(rawBackendUrl).origin;

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  async rewrites() {
    return {
      // beforeFiles are rewrites that are checked before any files on the filesystem.
      // We use this to ensure our local health check is not proxied.
      beforeFiles: [],
      // afterFiles are checked after pages and public files, but before dynamic routes.
      // This is where our main proxy to the backend lives.
      afterFiles: [
        {
          source: '/api/:path*',
          // Use the normalized origin for the destination to prevent path duplication.
          destination: `${backendApiOrigin}/api/:path*`,
        }
      ],
      // fallback rewrites are applied after both pages and dynamic routes are checked.
      fallback: [],
    };
  },

  // This is important for Docker deployments to reduce image size.
  output: 'standalone',
};

export default nextConfig;