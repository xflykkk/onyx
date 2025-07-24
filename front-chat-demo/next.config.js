/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  serverExternalPackages: [],
  allowedDevOrigins: ['172.16.3.94'],
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://172.16.3.94:8888/:path*',
      },
    ];
  },
  webpack: (config) => {
    config.resolve.fallback = {
      ...config.resolve.fallback,
      fs: false,
    };
    return config;
  },
};

module.exports = nextConfig;