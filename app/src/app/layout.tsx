import type { Metadata } from "next";
import { Inter, Outfit } from "next/font/google";
import "./globals.css";
import Link from "next/link";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
});

const outfit = Outfit({
  variable: "--font-heading",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Data Storm - Outlet Intelligence",
  description: "Advanced Outlet Business Intelligence and Prediction Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${outfit.variable} h-full antialiased dark`}
    >
      <body className="h-full bg-slate-950 text-slate-100 flex font-sans overflow-hidden">
        {/* Navigation Sidebar */}
        <aside className="w-64 border-r border-slate-800 bg-slate-900/60 backdrop-blur-md flex flex-col justify-between shrink-0">
          <div>
            {/* Logo */}
            <div className="p-6 border-b border-slate-800">
              <Link href="/" className="flex items-center gap-3 group">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-500 to-violet-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 group-hover:scale-105 transition-transform">
                  <span className="text-white font-extrabold text-sm">⚡</span>
                </div>
                <div>
                  <h1 className="font-heading font-bold text-lg tracking-tight text-white leading-none">Outlet Intelligence</h1>
                  <span className="text-[10px] text-slate-400 tracking-widest uppercase">Data Storm v7.0</span>
                </div>
              </Link>
            </div>

            {/* Menu Links */}
            <nav className="p-4 space-y-1">
              <Link 
                href="/" 
                className="flex items-center gap-3 px-4 py-3 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800/60 transition-all font-medium text-sm group"
              >
                <span className="text-lg group-hover:scale-110 transition-transform">📊</span>
                Dashboard
              </Link>
              <Link 
                href="/budget" 
                className="flex items-center gap-3 px-4 py-3 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800/60 transition-all font-medium text-sm group"
              >
                <span className="text-lg group-hover:scale-110 transition-transform">💰</span>
                WP Budget Spend
              </Link>
              <Link 
                href="/health" 
                className="flex items-center gap-3 px-4 py-3 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800/60 transition-all font-medium text-sm group"
              >
                <span className="text-lg group-hover:scale-110 transition-transform">🩺</span>
                Pipeline Health
              </Link>
            </nav>
          </div>

          {/* Footer Info */}
          <div className="p-4 border-t border-slate-800/60 text-center">
            <span className="text-[10px] text-slate-500 font-mono">Model Version: v7.0.4-LOCKED</span>
          </div>
        </aside>

        {/* Content Area */}
        <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
          {/* Top Bar */}
          <header className="h-16 border-b border-slate-800/60 bg-slate-950/40 backdrop-blur-md flex items-center justify-between px-8 sticky top-0 z-40">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="text-xs font-semibold text-slate-400 tracking-wider uppercase">Region: Sri Lanka</span>
            </div>
            <div className="flex items-center gap-4">
              <div className="px-3 py-1 rounded-full border border-slate-800 bg-slate-900/50 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
                <span className="text-xs text-slate-300 font-mono">API Connection: Active</span>
              </div>
            </div>
          </header>

          {/* Page Body */}
          <main className="flex-1 p-8">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
