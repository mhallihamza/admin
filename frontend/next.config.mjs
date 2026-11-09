/** @type {import('next').NextConfig} */
const nextConfig = {
  // Machine à RAM limitée : optimisations mémoire webpack (Next 15)
  experimental: {
    webpackMemoryOptimizations: true,
  },
};

export default nextConfig;
