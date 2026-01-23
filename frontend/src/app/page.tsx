import { Button } from "@/components/ui/button";

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
          <Button size="lg">Get Started</Button>
        </div>
      </div>
    </div>
  );
}
