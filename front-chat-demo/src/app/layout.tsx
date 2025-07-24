import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import '@/styles/globals.css';
import { cn } from '@/lib/utils';

const inter = Inter({ 
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

export const metadata: Metadata = {
  metadataBase: new URL('http://localhost:3000'),
  title: 'DeepInsight Chat - AI Document Assistant',
  description: 'Chat with your documents using AI-powered search and retrieval. Upload files and get instant answers with cited sources.',
  keywords: ['AI', 'chat', 'documents', 'search', 'retrieval', 'assistant', 'deepinsight'],
  authors: [{ name: 'DeepInsight Team' }],
  manifest: '/manifest.json',
  icons: {
    icon: [
      { url: '/favicon.ico', sizes: '32x32' },
    ],
  },
  openGraph: {
    type: 'website',
    siteName: 'DeepInsight Chat',
    title: 'DeepInsight Chat - AI Document Assistant',
    description: 'Chat with your documents using AI-powered search and retrieval',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'DeepInsight Chat - AI Document Assistant',
    description: 'Chat with your documents using AI-powered search and retrieval',
  },
  robots: {
    index: false,
    follow: false,
  },
};

export function generateViewport() {
  return {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 1,
    userScalable: false,
    themeColor: [
      { media: '(prefers-color-scheme: light)', color: '#667eea' },
      { media: '(prefers-color-scheme: dark)', color: '#764ba2' },
    ],
  };
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={cn(inter.variable, 'scroll-smooth')}>
      <body 
        className={cn(
          'font-sans antialiased',
          'bg-gradient-to-br from-slate-50 to-blue-50',
          'dark:from-slate-900 dark:to-blue-900',
          'transition-colors duration-300'
        )}
        suppressHydrationWarning={true}
      >
        {/* Accessibility Skip Link */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 z-50 px-4 py-2 bg-blue-600 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        >
          Skip to main content
        </a>

        {/* Background Effects */}
        <div className="fixed inset-0 overflow-hidden pointer-events-none">
          {/* Glassmorphism Background Orbs */}
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-gradient-to-r from-blue-400/20 to-purple-400/20 rounded-full blur-3xl animate-float" />
          <div className="absolute top-3/4 right-1/4 w-96 h-96 bg-gradient-to-r from-purple-400/20 to-pink-400/20 rounded-full blur-3xl animate-float" style={{ animationDelay: '2s' }} />
          <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-gradient-to-r from-pink-400/20 to-blue-400/20 rounded-full blur-3xl animate-float" style={{ animationDelay: '4s' }} />
        </div>

        {/* Main Content */}
        <div id="main-content" className="relative z-10">
          {children}
        </div>

        {/* Loading States and Accessibility */}
        <div id="loading-overlay" className="hidden fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="glass-effect rounded-xl p-6 flex items-center space-x-4">
            <div className="loading-spinner" />
            <span className="text-glass">Loading...</span>
          </div>
        </div>


        {/* Toast Container */}
        <div id="toast-container" className="fixed bottom-4 right-4 z-50 space-y-2 pointer-events-none" />

        {/* Preload Critical Resources */}
        <link rel="preload" href="/fonts/inter-var.woff2" as="font" type="font/woff2" crossOrigin="anonymous" />
        
        {/* Analytics and Monitoring (placeholder) */}
        {process.env.NODE_ENV === 'production' && (
          <>
            {/* Add your analytics scripts here */}
          </>
        )}
      </body>
    </html>
  );
}