import { z } from "zod";

export const createTaskSchema = z.object({
  projectId: z.string().uuid(),
  title: z.string().min(1, "Task title is required").max(200),
  description: z.string().max(5000).optional().nullable(),
  status: z.enum(["todo", "in_progress", "in_review", "done", "blocked"]).default("todo"),
  priority: z.enum(["low", "medium", "high", "urgent"]).default("medium"),
  assigneeId: z.string().uuid().optional().nullable(),
  dueDate: z.string().datetime().optional().nullable(),
  parentTaskId: z.string().uuid().optional().nullable(),
  estimatedHours: z.number().min(0).max(999).optional().nullable(),
});

export const updateTaskSchema = z.object({
  id: z.string().uuid(),
  title: z.string().min(1).max(200).optional(),
  description: z.string().max(5000).optional().nullable(),
  status: z.enum(["todo", "in_progress", "in_review", "done", "blocked"]).optional(),
  priority: z.enum(["low", "medium", "high", "urgent"]).optional(),
  assigneeId: z.string().uuid().optional().nullable(),
  dueDate: z.string().datetime().optional().nullable(),
  estimatedHours: z.number().min(0).max(999).optional().nullable(),
  actualHours: z.number().min(0).max(999).optional().nullable(),
  sortOrder: z.number().optional(),
});

export const updateTaskStatusSchema = z.object({
  id: z.string().uuid(),
  status: z.enum(["todo", "in_progress", "in_review", "done", "blocked"]),
  sortOrder: z.number().optional(),
});

export type CreateTaskInput = z.infer<typeof createTaskSchema>;
export type UpdateTaskInput = z.infer<typeof updateTaskSchema>;
export type UpdateTaskStatusInput = z.infer<typeof updateTaskStatusSchema>;
