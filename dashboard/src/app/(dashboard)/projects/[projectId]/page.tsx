import { getProject } from "@/modules/projects/actions";
import { getTasks } from "@/modules/tasks/actions";
import { KanbanBoard } from "@/components/projects/kanban-board";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { notFound } from "next/navigation";
import { formatDate } from "@/lib/utils";
import { PROJECT_STATUS_LABELS } from "@/types/database";
import type { TaskStatus, TaskWithMeta } from "@/types/database";
import { TaskList } from "@/components/projects/task-list";

export default async function ProjectDetailPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const project = await getProject(projectId);
  if (!project) notFound();

  let tasks: TaskWithMeta[] = [];
  try {
    tasks = await getTasks(projectId);
  } catch {
    // tasks may fail if no auth
  }

  const taskCount = tasks.length;
  const completedCount = tasks.filter((t: any) => t.status === "done").length;
  const progress = taskCount > 0 ? Math.round((completedCount / taskCount) * 100) : 0;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3 mb-2">
          <div
            className="h-4 w-4 rounded-full"
            style={{ backgroundColor: project.color }}
          />
          <h1 className="text-2xl font-bold tracking-tight">{project.name}</h1>
          <Badge variant="outline" className="text-xs">
            {PROJECT_STATUS_LABELS[project.status]}
          </Badge>
        </div>
        {project.description && (
          <p className="text-sm text-muted-foreground mt-1">{project.description}</p>
        )}
        <p className="text-xs text-muted-foreground mt-2">
          Created {formatDate(project.created_at)} • {taskCount} tasks • {progress}% complete
        </p>
      </div>

      {/* View Tabs */}
      <Tabs defaultValue="board">
        <TabsList>
          <TabsTrigger value="board">Board</TabsTrigger>
          <TabsTrigger value="list">List</TabsTrigger>
        </TabsList>
        <TabsContent value="board">
          <KanbanBoard projectId={projectId} initialTasks={tasks} />
        </TabsContent>
        <TabsContent value="list">
          <TaskList projectId={projectId} initialTasks={tasks} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
