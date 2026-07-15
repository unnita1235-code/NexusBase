"use client";

import { useSession } from "next-auth/react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ROLE_LABELS } from "@/types/database";

export default function SettingsPage() {
  const { data: session } = useSession();

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Manage your profile and workspace preferences
        </p>
      </div>

      {/* Profile */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Profile</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary text-primary-foreground text-xl font-bold">
              {(session?.user?.name || session?.user?.email || "U").charAt(0).toUpperCase()}
            </div>
            <div>
              <p className="font-medium">{session?.user?.name || "User"}</p>
              <p className="text-sm text-muted-foreground">{session?.user?.email}</p>
              {session?.user?.role && (
                <Badge variant="outline" className="mt-1 text-xs">
                  {ROLE_LABELS[session.user.role as keyof typeof ROLE_LABELS] || session.user.role}
                </Badge>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Workspace */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Workspace</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Organization settings and branding will be available in Phase 4.
          </p>
        </CardContent>
      </Card>

      {/* Notifications */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Notifications</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Notification preferences will be available in Phase 2.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
