/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ['three'],
  images: {
    domains: ['prod.spline.design'],
  },
}

module.exports = nextConfig
