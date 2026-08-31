/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    serverComponentsExternalPackages: ["sharp", "@napi-rs/canvas"],
  },
};

module.exports = nextConfig;
