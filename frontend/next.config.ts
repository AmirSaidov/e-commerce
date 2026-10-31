import type { NextConfig } from "next";
import type { RemotePattern } from "next/dist/shared/lib/image-config";

// Хост, с которого Django отдаёт media/ (локально — localhost:8000, в проде — S3/Cloudinary/R2).
function mediaPatterns(): RemotePattern[] {
  const patterns: RemotePattern[] = [
    { protocol: "http", hostname: "localhost", port: "8000" },
    { protocol: "http", hostname: "127.0.0.1", port: "8000" },
    { protocol: "https", hostname: "res.cloudinary.com" },
    { protocol: "https", hostname: "*.r2.dev" },
  ];
  const mediaUrl = process.env.NEXT_PUBLIC_MEDIA_URL;
  if (mediaUrl) {
    const url = new URL(mediaUrl);
    patterns.push({
      protocol: url.protocol.replace(":", "") as "http" | "https",
      hostname: url.hostname,
      port: url.port,
    });
  }
  return patterns;
}

const nextConfig: NextConfig = {
  output: "standalone",
  images: {
    remotePatterns: mediaPatterns(),
  },
};

export default nextConfig;
