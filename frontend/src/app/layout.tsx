import type { Metadata } from "next";
import { Bebas_Neue, IBM_Plex_Sans, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/contexts/AuthContext";

const displayFont = Bebas_Neue({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-display",
});

const bodyFont = IBM_Plex_Sans({
  weight: ["400", "500", "600", "700"],
  subsets: ["latin"],
  variable: "--font-body",
});

const monoFont = JetBrains_Mono({
  weight: ["400", "500"],
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "SkyFi IntelliCheck",
  description: "Enterprise verification dashboard for SkyFi operators.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${displayFont.variable} ${bodyFont.variable} ${monoFont.variable}`} suppressHydrationWarning>
        <AuthProvider>
          <div id="root">{children}</div>
        </AuthProvider>
      </body>
    </html>
  );
}
