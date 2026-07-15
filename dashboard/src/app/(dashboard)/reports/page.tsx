import { Card, CardContent } from "@/components/ui/card";
import { BarChart3 } from "lucide-react";

export default function ReportsPage() {
  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Reports</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Analytics and insights across your projects
        </p>
      </div>
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-16">
          <BarChart3 className="h-10 w-10 text-muted-foreground mb-3" />
          <p className="text-sm font-medium">Reporting coming in Phase 3</p>
          <p className="text-xs text-muted-foreground mt-1">
            Burndown charts, velocity tracking, and PDF exports will be available soon
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
