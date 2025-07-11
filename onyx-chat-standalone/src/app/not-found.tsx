import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center glass-effect gradient-bg-1">
      <div className="text-center p-8 max-w-md mx-auto">
        <h1 className="text-6xl font-bold text-white mb-4">404</h1>
        <h2 className="text-2xl font-semibold text-white mb-4">
          Page Not Found
        </h2>
        <p className="text-gray-300 mb-6">
          The page you are looking for does not exist.
        </p>
        <Link
          href="/"
          className="inline-block px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
        >
          Go Home
        </Link>
      </div>
    </div>
  );
}