export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-center font-mono text-sm">
        <h1 className="text-4xl font-bold text-center mb-8">
          Market Data Hub
        </h1>
        <p className="text-xl text-center text-muted-foreground mb-4">
          Local High-Availability Market Data Hub
        </p>
        <p className="text-center text-muted-foreground">
          Dashboard for monitoring and managing market data aggregation and distribution
        </p>
      </div>
    </main>
  );
}