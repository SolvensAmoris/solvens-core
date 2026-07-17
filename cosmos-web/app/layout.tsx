import type { Metadata } from 'next'
import { Analytics } from '@vercel/analytics/react'
import { SpeedInsights } from '@vercel/speed-insights/next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Cosmos Compiler - Stop $2M outages before they ship',
  description: 'Terraform validates syntax. We validate time. Compile-time E401 detection for temporal infrastructure. 100x faster than Terraform validate.',
  keywords: ['cosmos', 'compiler', 'infrastructure', 'E401', 'temporal', 'terraform', 'validation', 'DAG', 'workflow'],
  authors: [{ name: 'Luis Alberto Burciaga Miker' }],
  openGraph: {
    title: 'Cosmos Compiler',
    description: 'Stop $2M outages before they ship',
    type: 'website',
    locale: 'en_US',
    siteName: 'Cosmos',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Cosmos Compiler',
    description: 'Stop $2M outages before they ship',
  },
  robots: {
    index: true,
    follow: true,
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
      </head>
      <body className="bg-black text-white antialiased">
        {children}
        <Analytics />
        <SpeedInsights />
      </body>
    </html>
  )
}
