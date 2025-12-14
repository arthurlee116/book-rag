const path = require("path");

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Helps SSE proxying (avoids compression buffering when proxying `text/event-stream`).
  compress: false,
  turbopack: {
    // Fix Next.js 16 workspace root inference when multiple lockfiles exist outside the repo.
    root: path.join(__dirname)
  },
  async rewrites() {
    const backendInternalUrl = process.env.BACKEND_INTERNAL_URL || "http://localhost:8000";
    return [
      {
        source: "/backend/:path*",
        destination: `${backendInternalUrl}/:path*`
      }
    ];
  }
};

module.exports = nextConfig;
