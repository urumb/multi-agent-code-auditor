import type { Metadata } from "next";
import { Geist, Geist_Mono, Instrument_Serif } from "next/font/google";
import "./globals.css";
import { Header } from "@/components/layout/header";
import { Toaster } from "sonner";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

const instrument = Instrument_Serif({
  variable: "--font-instrument",
  subsets: ["latin"],
  weight: "400",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Multi-Agent Code Auditor",
  description:
    "AI-powered multi-agent code analysis platform for security, performance, and code quality auditing.",
};

/**
 * Root layout: floating top navigation and a centered content column.
 */
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${geistSans.variable} ${geistMono.variable} ${instrument.variable} antialiased`}>
        <Header />
        <main className="mx-auto w-full max-w-6xl px-5 pb-24 pt-28 sm:px-8">
          {children}
        </main>
        <Toaster
          position="bottom-right"
          toastOptions={{
            style: {
              background: "#101013",
              border: "1px solid #212126",
              color: "#f1eee6",
              borderRadius: "14px",
            },
          }}
        />
      </body>
    </html>
  );
}
