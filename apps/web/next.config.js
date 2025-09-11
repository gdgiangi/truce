/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    ADJUDICATOR_API_URL: process.env.ADJUDICATOR_API_URL || 'http://localhost:8000',
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
