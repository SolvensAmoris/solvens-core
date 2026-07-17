import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Solvens Studio - AI-Native IDE",
  description: "The VS Code for AI Agents. Build, simulate, and deploy workflows.",
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
          href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen bg-[#0a0a0f] text-white antialiased font-sans">
        <div className="flex h-screen flex-col">
          {/* Header */}
          <header className="flex h-12 shrink-0 items-center justify-between border-b border-[#1a1a24] bg-[#0f0f14] px-4">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <span className="text-xl">🌵</span>
                <span className="font-bold gradient-text">SOLVENS</span>
                <span className="text-xs text-gray-500">STUDIO</span>
              </div>
              
              {/* File tabs */}
              <div className="flex items-center gap-1 ml-4">
                <div className="flex items-center gap-2 rounded bg-[#1a1a24] px-3 py-1 text-sm">
                  <span className="text-gray-400">crm_generator.cosmos</span>
                  <button className="text-gray-600 hover:text-white">×</button>
                </div>
                <button className="rounded px-2 py-1 text-sm text-gray-500 hover:bg-[#1a1a24]">+</button>
              </div>
            </div>
            
            {/* Actions */}
            <div className="flex items-center gap-2">
              <button className="flex items-center gap-2 rounded bg-[#22c55e]/20 px-3 py-1.5 text-sm text-[#22c55e]">
                <span>▶</span> Run
              </button>
              <button className="flex items-center gap-2 rounded bg-[#6366f1]/20 px-3 py-1.5 text-sm text-[#6366f1]">
                <span>🔮</span> Simulate
              </button>
              <button className="flex items-center gap-2 rounded bg-[#f59e0b]/20 px-3 py-1.5 text-sm text-[#f59e0b]">
                <span>🚀</span> Deploy
              </button>
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
