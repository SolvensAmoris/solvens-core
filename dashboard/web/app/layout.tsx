import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SOLVENS CORE Dashboard",
  description: "Real-time DAG visualization for AI Agent orchestration",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen bg-[#0f0f13] text-white antialiased">
        <div className="flex h-screen flex-col">
          {/* Header */}
          <header className="flex h-14 shrink-0 items-center justify-between border-b border-[#2a2a3a] bg-[#16161d] px-6">
            <div className="flex items-center gap-3">
              <div className="text-xl font-bold gradient-text">🌵 SOLVENS CORE</div>
              <span className="text-xs text-[#8888aa]">v1.0.0</span>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-xs text-[#8888aa]">
                Dashboard
              </span>
              <div className="h-2 w-2 rounded-full bg-green-500"></div>
            </div>
          </header>
          
          {/* Main content */}
          <main className="flex-1 overflow-hidden">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
