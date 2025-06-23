/** @type {import('next').NextConfig} */
const nextConfig = {
  // App directory is now default in Next.js 14+, no experimental flag needed
  // Enable standalone output for Docker
  output: "standalone",
  // Transpile packages from the monorepo
  transpilePackages: ["@xiaoy-mdhub/shared-types", "@xiaoy-mdhub/ui"],
  // Environment variables
  env: {
    NEXT_PUBLIC_API_URL:
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000",
  },
  // Image domains (if needed for external images)
  images: {
    domains: [],
  },
  // Rewrites for API proxy (optional)
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/:path*`,
      },
    ];
  },
  // Headers for security
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "Referrer-Policy",
            value: "origin-when-cross-origin",
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
