export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`bg-slate-200 rounded-lg animate-pulse ${className}`}
      aria-hidden="true"
    />
  );
}

export function PredictionCardSkeleton() {
  return (
    <article className="bg-white rounded-2xl shadow-card p-5">
      <div className="flex items-start justify-between mb-3">
        <div className="space-y-2 flex-1">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-3 w-24" />
        </div>
      </div>
      <Skeleton className="h-10 w-20 mb-2" />
      <Skeleton className="h-3 w-40 mb-3" />
      <div className="grid grid-cols-2 gap-2">
        <Skeleton className="h-12" />
        <Skeleton className="h-12" />
      </div>
      <Skeleton className="h-3 w-24 mt-4" />
    </article>
  );
}
