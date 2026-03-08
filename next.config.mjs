/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  basePath: '/MoDora',
  assetPrefix: '/MoDora/',
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
