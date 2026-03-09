import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { Toaster } from "sonner";
import { PageTransition } from "@/components/layout/page-transition";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Multi-Agent Code Auditor",
  description:
    "AI-powered multi-agent code analysis platform for security, performance, and code quality auditing.",
};

/**
 * Root layout with sidebar navigation, top header, and scrollable content area.
 * Dark theme is applied by default via the `dark` class on the html element.
 */
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-[radial-gradient(circle_at_top,_#1e293b,_#020617)]`}
      >
        <div className="flex h-screen bg-background overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-y-auto flex flex-col">
            <Header />
            <div className="p-8 w-full max-w-7xl mx-auto">
              <PageTransition>{children}</PageTransition>
            </div>
          </main>
        </div>
        <Toaster
          position="bottom-right"
          toastOptions={{
            style: {
              background: "#1e293b", /* slate-800 */
              border: "1px solid #334155", /* slate-700 */
              color: "#f8fafc", /* slate-50 */
            },
          }}
        />
      </body>
    </html>
  );
}
