"use client";

import Link from "next/link";
import { useState } from "react";
import { Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";

/* Satu-satunya bagian landing yang butuh 'use client' — sisanya Server Component
   (guideline nextjs: "Don't add 'use client' unnecessarily"). */

const LINKS = [
  { href: "#fitur", label: "Fitur" },
  { href: "#cara-kerja", label: "Cara Kerja" },
  { href: "#use-case", label: "Use Case" },
];

export function LandingNav() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b bg-background/90 backdrop-blur">
      <nav
        aria-label="Navigasi utama"
        className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-4 sm:px-6"
      >
        <Link href="/" className="flex items-center gap-2 no-underline">
          <span
            className="flex h-8 w-8 items-center justify-center rounded bg-primary font-bold text-primary-foreground"
            aria-hidden="true"
          >
            D
          </span>
          <span className="text-lg font-extrabold tracking-wider text-foreground">
            DATA<span className="text-primary">KLIN</span>
          </span>
        </Link>

        <ul className="ml-4 hidden items-center gap-1 md:flex">
          {LINKS.map((l) => (
            <li key={l.href}>
              <a
                href={l.href}
                className="inline-flex h-11 items-center rounded-md px-3 text-sm font-medium text-muted-foreground no-underline transition-colors duration-200 hover:bg-secondary hover:text-secondary-foreground"
              >
                {l.label}
              </a>
            </li>
          ))}
        </ul>

        <div className="ml-auto flex items-center gap-1">
          <ThemeToggle />
          {/* CTA di nav — MASTER: "Primary CTA in nav + After metrics" */}
          <Button
            size="lg"
            className="hidden md:inline-flex"
            render={<Link href="/login" />}
            nativeButton={false}
          >
            Masuk ke Dataklin
          </Button>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-label={open ? "Tutup menu" : "Buka menu"}
            aria-expanded={open}
            aria-controls="menu-mobile"
            className="inline-flex h-11 w-11 cursor-pointer items-center justify-center rounded-md text-muted-foreground transition-colors duration-200 hover:bg-secondary hover:text-secondary-foreground md:hidden"
          >
            {open ? (
              <X className="h-5 w-5" aria-hidden="true" />
            ) : (
              <Menu className="h-5 w-5" aria-hidden="true" />
            )}
          </button>
        </div>
      </nav>

      {/* Menu mobile dirender hanya saat terbuka: tidak ada elemen fokusabel tersembunyi */}
      {open && (
        <div id="menu-mobile" className="border-t bg-background md:hidden">
          <ul className="mx-auto max-w-6xl px-4 py-2 sm:px-6">
            {LINKS.map((l) => (
              <li key={l.href}>
                <a
                  href={l.href}
                  onClick={() => setOpen(false)}
                  className="flex h-12 items-center text-sm font-medium text-foreground no-underline"
                >
                  {l.label}
                </a>
              </li>
            ))}
            <li className="py-2">
              <Button
                size="lg"
                className="w-full"
                render={<Link href="/login" />}
                nativeButton={false}
              >
                Masuk ke Dataklin
              </Button>
            </li>
          </ul>
        </div>
      )}
    </header>
  );
}
