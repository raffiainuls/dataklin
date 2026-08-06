"use client";

import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";

/* Toggle tema tanpa dependensi tambahan (next-themes tidak dipasang).
   Sinkron dengan inline script di app/layout.tsx yang membaca kunci yang sama. */
export function ThemeToggle({ className = "" }: { className?: string }) {
  const [dark, setDark] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
    setMounted(true);
  }, []);

  function toggle() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem("dataklin_theme", next ? "dark" : "light");
    } catch {
      /* localStorage bisa diblokir; tema tetap berubah untuk sesi ini */
    }
  }

  return (
    <button
      type="button"
      onClick={toggle}
      /* aria-label wajib: tombol ikon tanpa teks (ux-guidelines: ARIA Labels, severity High) */
      aria-label={dark ? "Ganti ke mode terang" : "Ganti ke mode gelap"}
      aria-pressed={dark}
      title={dark ? "Mode terang" : "Mode gelap"}
      /* min 44x44px area sentuh (ux-guidelines: Touch & Interaction, CRITICAL) */
      className={`inline-flex h-11 w-11 cursor-pointer items-center justify-center rounded-md text-muted-foreground transition-colors duration-200 hover:bg-accent/10 hover:text-foreground ${className}`}
    >
      {/* suppressHydrationWarning: ikon awal bergantung tema yang di-set script sebelum hydrate */}
      <span suppressHydrationWarning>
        {mounted && dark ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
      </span>
    </button>
  );
}
