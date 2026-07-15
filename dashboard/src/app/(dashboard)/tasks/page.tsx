import { getMyTasks } from "@/modules/tasks/actions";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { formatDate, getPriorityColor, getStatusColor } from "@/lib/utils";
import { TASK_PRIORITY_LABELS, TASK_STATUS_LABELS } from "@/types/database";
import type { TaskWithMeta } from "@/types/database";

export default async function MyTasksPage() {
  let tasks: TaskWithMeta[] = [];
  try {
    tasks = await getMyTasks();
  } catch {
    // no org
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">My Tasks</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Tasks assigned to you across all projects
        </p>
      </div>

      {tasks.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <p className="text-sm font-medium">No tasks assigned to you</p>
            <p className="text-xs text-muted-foreground mt-1">
              You're all caught up!
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[40%]">Task</TableHead>
                <TableHead>Project</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Priority</TableHead>
                <TableHead>Due Date</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tasks.map((task) => (
                <TableRow key={task.id}>
                  <TableCell className="font-medium">{task.title}</TableCell>
                  <TableCell>
                    {task.project && (
                      <Link
                        href={`/projects/${task.project_id}`}
                        className="flex items-center gap-2 text-sm hover:underline"
                      >
                        <div
                          className="h-2 w-2 rounded-full"
                          style={{ backgroundColor: task.project.color }}
                        />
                        {task.project.name}
                      </Link>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className={`text-xs ${getStatusColor(task.status)}`}>
                      {TASK_STATUS_LABELS[task.status]}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className={`text-xs ${getPriorityColor(task.priority)}`}>
                      {TASK_PRIORITY_LABELS[task.priority]}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDate(task.due_date)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
