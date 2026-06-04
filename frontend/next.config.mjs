/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Backend has no CI here; don't fail the build on lint.
  eslint: { ignoreDuringBuilds: true },
};

export default nextConfig;
