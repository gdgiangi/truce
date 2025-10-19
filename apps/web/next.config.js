/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    ADJUDICATOR_API_URL: process.env.ADJUDICATOR_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_ADJUDICATOR_API_URL: process.env.NEXT_PUBLIC_ADJUDICATOR_API_URL || 'http://localhost:8000',
  },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'registry.npmmirror.com',
        port: '',
        pathname: '/**',
      },
    ],
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.ADJUDICATOR_API_URL || 'http://localhost:8000'}/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
