const path = require("path");

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  turbopack: {
    // Fix Next.js 16 workspace root inference when multiple lockfiles exist outside the repo.
    root: path.join(__dirname)
  }
};

module.exports = nextConfig;
