import type { Metadata } from "next";
import "./globals.css";
import { Fira_Sans, Fira_Code } from "next/font/google";
import { cn } from "@/lib/utils";

/* Tipografi dari design-system/dataklin/MASTER.md:
   body Fira Sans, angka & label data Fira Code — mood "dashboard, data, precise". */
const firaSans = Fira_Sans({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-sans",
  display: "swap",
});

const firaCode = Fira_Code({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Dataklin — Data Quality Platform",
  description: "AI-Powered Data Quality & Entity Resolution Platform",
};

/* Set kelas .dark sebelum paint supaya tidak ada flash tema terang.
   Inline script dipakai karena project tidak memakai next-themes. */
const themeInit = `(function(){try{var t=localStorage.getItem("dataklin_theme");if(t==="dark"||(!t&&window.matchMedia("(prefers-color-scheme: dark)").matches)){document.documentElement.classList.add("dark")}}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInit }} />
      </head>
      <body
        className={cn(
          "min-h-screen bg-background font-sans antialiased",
          firaSans.variable,
          firaCode.variable,
        )}
      >
        {children}
      </body>
    </html>
  );
}
