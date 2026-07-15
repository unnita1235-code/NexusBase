import { getProjects } from "@/modules/projects/actions";
import { getMyTasks } from "@/modules/tasks/actions";
import { auth } from "@/auth";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import {
  FolderKanban,
  CheckCircle2,
  Clock,
  AlertCircle,
  TrendingUp,
} from "lucide-react";
import { formatDate, getPriorityColor } from "@/lib/utils";
import { TASK_PRIORITY_LABELS } from "@/types/database";
import type { Project, TaskWithMeta } from "@/types/database";

export default async function DashboardPage() {
  const session = await auth();
  let projects: Project[] = [];
  let myTasks: TaskWithMeta[] = [];

  try {
    projects = await getProjects();
    myTasks = await getMyTasks();
  } catch {
    // User may not have an org yet
  }

  const activeProjects = projects.filter((p) => p.status === "active");
  const completedProjects = projects.filter((p) => p.status === "completed");
  const overdueTasks = myTasks.filter(
    (t) => t.due_date && new Date(t.due_date) < new Date()
  );

  const stats = [
    {
      label: "Active Projects",
      value: activeProjects.length,
      icon: FolderKanban,
      color: "text-blue-600",
    },
    {
      label: "My Open Tasks",
      value: myTasks.length,
      icon: CheckCircle2,
      color: "text-green-600",
    },
    {
      label: "Overdue Tasks",
      value: overdueTasks.length,
      icon: AlertCircle,
      color: "text-red-600",
    },
    {
      label: "Completed Projects",
      value: completedProjects.length,
      icon: TrendingUp,
      color: "text-purple-600",
    },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          Welcome back, {session?.user?.name || session?.user?.email?.split("@")[0] || "User"}
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Here's an overview of your workspace
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.label}>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">{stat.label}</p>
                    <p className="text-2xl font-bold mt-1">{stat.value}</p>
                  </div>
                  <div className={`p-2 rounded-lg bg-muted ${stat.color}`}>
                    <Icon className="h-5 w-5" />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active Projects */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Active Projects</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {activeProjects.length === 0 ? (
              <div className="text-center py-8 text-sm text-muted-foreground">
                No active projects yet.{" "}
                <Link href="/projects/new" className="text-primary hover:underline">
                  Create one
                </Link>
              </div>
            ) : (
              activeProjects.slice(0, 5).map((project) => (
                <Link
                  key={project.id}
                  href={`/projects/${project.id}`}
                  className="flex items-center gap-3 rounded-md border border-border p-3 hover:bg-muted/50 transition-colors"
                >
                  <div
                    className="h-3 w-3 rounded-full shrink-0"
                    style={{ backgroundColor: project.color }}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{project.name}</p>
                    <p className="text-xs text-muted-foreground">
                      Created {formatDate(project.created_at)}
                    </p>
                  </div>
                </Link>
              ))
            )}
          </CardContent>
        </Card>

        {/* My Tasks */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">My Tasks</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {myTasks.length === 0 ? (
              <div className="text-center py-8 text-sm text-muted-foreground">
                No tasks assigned to you. All caught up!
              </div>
            ) : (
              myTasks.slice(0, 5).map((task) => (
                <Link
                  key={task.id}
                  href={`/projects/${task.project_id}`}
                  className="flex items-center gap-3 rounded-md border border-border p-3 hover:bg-muted/50 transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{task.title}</p>
                    <div className="flex items-center gap-2 mt-1">
                      {task.project && (
                        <span className="text-xs text-muted-foreground">{task.project.name}</span>
                      )}
                      {task.due_date && (
                        <span className="text-xs text-muted-foreground">
                          • Due {formatDate(task.due_date)}
                        </span>
                      )}
                    </div>
                  </div>
                  <Badge
                    variant="outline"
                    className={`text-xs ${getPriorityColor(task.priority)}`}
                  >
                    {TASK_PRIORITY_LABELS[task.priority]}
                  </Badge>
                </Link>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
