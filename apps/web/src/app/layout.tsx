import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/toaster";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  fallback: ["system-ui", "-apple-system", "sans-serif"],
});

export const metadata: Metadata = {
  title: "Market Data Hub",
  description: "Local High-Availability Market Data Hub Dashboard",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <div className="min-h-screen bg-background">
          <nav className="border-b">
            <div className="container mx-auto px-4 py-3">
              <div className="flex justify-between items-center">
                <h1 className="text-lg font-semibold">Market Data Hub</h1>
                <div className="flex space-x-4">
                  <a href="/" className="text-sm text-muted-foreground hover:text-foreground">
                    Home
                  </a>
                  <a href="/accounts" className="text-sm text-muted-foreground hover:text-foreground">
                    Accounts
                  </a>
                  <a href="/logs" className="text-sm text-muted-foreground hover:text-foreground">
                    Logs
                  </a>
                </div>
              </div>
            </div>
          </nav>
          {children}
          <Toaster />
        </div>
      </body>
    </html>
  );
}
