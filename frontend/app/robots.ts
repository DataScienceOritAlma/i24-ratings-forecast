import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: [
          "/dashboard",
          "/chat",
          "/history",
          "/analytics",
          "/account",
        ],
      },
    ],
    sitemap: "https://i24-ratings-forecast.vercel.app/sitemap.xml",
  };
}
