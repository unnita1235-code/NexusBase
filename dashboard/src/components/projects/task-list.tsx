"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
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

interface TaskListProps {
  projectId: string;
  initialTasks: TaskWithMeta[];
}

export function TaskList({ projectId, initialTasks }: TaskListProps) {
  const [tasks] = useState(initialTasks);

  if (tasks.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-border p-12 text-center">
        <p className="text-sm text-muted-foreground">No tasks yet. Switch to Board view to add tasks.</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[40%]">Task</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Priority</TableHead>
            <TableHead>Assignee</TableHead>
            <TableHead>Due Date</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {tasks.map((task) => (
            <TableRow key={task.id}>
              <TableCell className="font-medium">{task.title}</TableCell>
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
                {task.assignee?.email?.split("@")[0] ?? "—"}
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {formatDate(task.due_date)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
