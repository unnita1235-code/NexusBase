"use client";

import { useState, useCallback } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
  useDroppable,
} from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
  arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { updateTaskStatus, createTask, deleteTask } from "@/modules/tasks/actions";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Plus, Trash2, GripVertical, Calendar } from "lucide-react";
import { toast } from "sonner";
import { formatDate, getPriorityColor, getStatusColor } from "@/lib/utils";
import type { Task, TaskStatus, TaskWithMeta } from "@/types/database";
import { TASK_STATUSES, TASK_STATUS_LABELS, TASK_PRIORITY_LABELS } from "@/types/database";

interface KanbanBoardProps {
  projectId: string;
  initialTasks: TaskWithMeta[];
}

function SortableTaskCard({ task, projectId }: { task: Task; projectId: string }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: task.id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className="group relative rounded-md border border-border bg-card p-3 shadow-sm hover:shadow-md transition-shadow cursor-grab active:cursor-grabbing"
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium flex-1">{task.title}</p>
        <GripVertical className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>
      {task.description && (
        <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{task.description}</p>
      )}
      <div className="flex items-center gap-2 mt-2">
        <Badge variant="outline" className={`text-xs ${getPriorityColor(task.priority)}`}>
          {TASK_PRIORITY_LABELS[task.priority]}
        </Badge>
        {task.due_date && (
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <Calendar className="h-3 w-3" />
            {formatDate(task.due_date)}
          </span>
        )}
      </div>
      <button
        onClick={(e) => {
          e.stopPropagation();
          if (confirm("Delete this task?")) {
            deleteTask(task.id, projectId).then(() => toast.success("Task deleted"));
          }
        }}
        className="absolute top-1 right-1 p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-destructive/10 transition-all"
        title="Delete task"
      >
        <Trash2 className="h-3 w-3 text-destructive" />
      </button>
    </div>
  );
}

function KanbanColumn({
  status,
  tasks,
  onAddTask,
  projectId,
}: {
  status: TaskStatus;
  tasks: TaskWithMeta[];
  onAddTask: (status: TaskStatus) => void;
  projectId: string;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: `column-${status}` });

  return (
    <div className="flex flex-col min-w-[280px] w-80">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(status)}`}>
            {TASK_STATUS_LABELS[status]}
          </span>
          <span className="text-xs text-muted-foreground">{tasks.length}</span>
        </div>
        <button
          onClick={() => onAddTask(status)}
          className="p-1 rounded hover:bg-muted transition-colors"
          title="Add task"
        >
          <Plus className="h-4 w-4 text-muted-foreground" />
        </button>
      </div>
      <div
        ref={setNodeRef}
        className={`flex-1 space-y-2 rounded-lg p-2 min-h-[200px] transition-colors ${
          isOver ? "bg-muted/50" : "bg-muted/20"
        }`}
      >
        <SortableContext items={tasks.map((t) => t.id)} strategy={verticalListSortingStrategy}>
          {tasks.map((task) => (
            <SortableTaskCard key={task.id} task={task} projectId={projectId} />
          ))}
        </SortableContext>
        {tasks.length === 0 && (
          <button
            onClick={() => onAddTask(status)}
            className="w-full text-xs text-muted-foreground py-4 hover:bg-muted/30 rounded-md transition-colors"
          >
            + Add task
          </button>
        )}
      </div>
    </div>
  );
}

export function KanbanBoard({ projectId, initialTasks }: KanbanBoardProps) {
  const [tasks, setTasks] = useState<TaskWithMeta[]>(initialTasks);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [addingToColumn, setAddingToColumn] = useState<TaskStatus | null>(null);
  const [newTaskTitle, setNewTaskTitle] = useState("");
  const [isAdding, setIsAdding] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  const tasksByStatus = (status: TaskStatus) =>
    tasks.filter((t) => t.status === status).sort((a, b) => a.sort_order - b.sort_order);

  const activeTask = activeId ? tasks.find((t) => t.id === activeId) : null;

  const handleDragStart = (e: DragStartEvent) => {
    setActiveId(e.active.id as string);
  };

  const handleDragEnd = useCallback(
    async (e: DragEndEvent) => {
      setActiveId(null);
      const { active, over } = e;
      if (!over) return;

      const activeTaskId = active.id as string;
      const task = tasks.find((t) => t.id === activeTaskId);
      if (!task) return;

      let newStatus = task.status;
      let newSortOrder = task.sort_order;

      if (over.id.toString().startsWith("column-")) {
        newStatus = over.id.toString().replace("column-", "") as TaskStatus;
        const columnTasks = tasksByStatus(newStatus);
        newSortOrder = columnTasks.length > 0 ? Math.max(...columnTasks.map((t) => t.sort_order)) + 1 : 0;
      } else {
        const overTask = tasks.find((t) => t.id === over.id);
        if (!overTask) return;
        newStatus = overTask.status;
        newSortOrder = overTask.sort_order;
      }

      if (newStatus === task.status && newSortOrder === task.sort_order) return;

      setTasks((prev) =>
        prev.map((t) =>
          t.id === activeTaskId ? { ...t, status: newStatus, sort_order: newSortOrder } : t
        )
      );

      try {
        await updateTaskStatus({ id: activeTaskId, status: newStatus, sortOrder: newSortOrder });
      } catch (err) {
        toast.error("Failed to update task status");
        setTasks(initialTasks);
      }
    },
    [tasks, initialTasks]
  );

  const handleAddTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTaskTitle.trim() || !addingToColumn) return;

    setIsAdding(true);
    try {
      const task = await createTask({
        projectId,
        title: newTaskTitle,
        status: addingToColumn,
      });
      setTasks((prev) => [...prev, task]);
      setNewTaskTitle("");
      setAddingToColumn(null);
      toast.success("Task created");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create task");
    } finally {
      setIsAdding(false);
    }
  };

  return (
    <div className="space-y-4">
      <DndContext
        sensors={sensors}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="flex gap-4 overflow-x-auto pb-4">
          {TASK_STATUSES.map((status) => (
            <KanbanColumn
              key={status}
              status={status}
              tasks={tasksByStatus(status)}
              onAddTask={(s) => {
                setAddingToColumn(s);
                setNewTaskTitle("");
              }}
              projectId={projectId}
            />
          ))}
        </div>
        <DragOverlay>
          {activeTask ? (
            <div className="rounded-md border border-border bg-card p-3 shadow-lg opacity-90">
              <p className="text-sm font-medium">{activeTask.title}</p>
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>

      {/* Add Task Dialog */}
      {addingToColumn && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setAddingToColumn(null)}>
          <div className="w-full max-w-md rounded-lg border border-border bg-card p-6 shadow-lg" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-sm font-semibold mb-3">
              New Task — {TASK_STATUS_LABELS[addingToColumn]}
            </h3>
            <form onSubmit={handleAddTask} className="space-y-3">
              <Input
                value={newTaskTitle}
                onChange={(e) => setNewTaskTitle(e.target.value)}
                placeholder="Task title..."
                autoFocus
              />
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" size="sm" onClick={() => setAddingToColumn(null)}>
                  Cancel
                </Button>
                <Button type="submit" size="sm" disabled={isAdding || !newTaskTitle.trim()}>
                  Add Task
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
