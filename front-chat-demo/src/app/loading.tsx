export default function Loading() {
  return (
    <div className="min-h-screen flex items-center justify-center glass-effect gradient-bg-1">
      <div className="text-center p-8">
        <div className="loading-spinner mx-auto mb-4"></div>
        <p className="text-white text-lg">Loading...</p>
      </div>
    </div>
  );
}