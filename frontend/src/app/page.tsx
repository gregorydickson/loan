export default function Home() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="space-y-6 text-center">
        <h1 className="text-4xl font-bold tracking-tight">
          Loan Document Extraction
        </h1>
        <p className="max-w-md text-lg text-muted-foreground">
          Extract and organize borrower data from loan documents with complete source traceability
        </p>
        <div className="pt-4">
          <span className="inline-block rounded-lg bg-foreground px-6 py-3 text-background font-medium">
            Get Started
          </span>
        </div>
      </div>
    </div>
  );
}
