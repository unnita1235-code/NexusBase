import { Card, CardContent } from "@/components/ui/card";
import { Users } from "lucide-react";

export default function TeamPage() {
  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Team</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Manage team members and invitations
        </p>
      </div>
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-16">
          <Users className="h-10 w-10 text-muted-foreground mb-3" />
          <p className="text-sm font-medium">Team management coming in Phase 2</p>
          <p className="text-xs text-muted-foreground mt-1">
            Member invitations, roles, and real-time collaboration will be available soon
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
