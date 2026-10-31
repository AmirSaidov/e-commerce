import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import { Footer } from "@/components/layout/footer";
import { Header } from "@/components/layout/header";
import { Providers } from "@/components/providers";
import { api } from "@/lib/api";
import type { Category } from "@/lib/api/types";
import { SITE_NAME, SITE_URL } from "@/lib/config";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin", "cyrillic"],
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: `${SITE_NAME} — магазин электроники и гаджетов`,
    template: `%s — ${SITE_NAME}`,
  },
  description:
    "Смартфоны, ноутбуки, наушники, умные часы и игровые консоли. Официальная гарантия, быстрая доставка и удобная оплата.",
  openGraph: {
    type: "website",
    locale: "ru_RU",
    siteName: SITE_NAME,
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#fcfcfe" },
    { media: "(prefers-color-scheme: dark)", color: "#16161d" },
  ],
};

async function loadCategories(): Promise<Category[]> {
  try {
    return await api.catalog.categories();
  } catch {
    // Если бэкенд недоступен, шапка просто останется без категорий
    return [];
  }
}

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const categories = await loadCategories();
  return (
    <html lang="ru" suppressHydrationWarning>
      <body className={`${inter.variable} flex min-h-dvh flex-col font-sans antialiased`}>
        <Providers>
          <a
            href="#main"
            className="bg-primary text-primary-foreground sr-only z-50 rounded-md px-4 py-2 focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
          >
            Перейти к содержимому
          </a>
          <Header categories={categories} />
          <main id="main" className="flex-1">
            {children}
          </main>
          <Footer categories={categories} />
        </Providers>
      </body>
    </html>
  );
}
