import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Serve the static showcase pages at clean, app-native URLs (no ".html").
  // These are rewrites (not React routes) — they serve the public files as-is,
  // so they can't hit the render failures the route approach did (שלבים 70-71).
  async rewrites() {
    return [
      { source: "/about", destination: "/index.html" },
      { source: "/infographic", destination: "/infographic.html" },
    ];
  },
};

export default nextConfig;
