"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import { auth } from "@/auth";
import {
  createTaskSchema,
  updateTaskSchema,
  updateTaskStatusSchema,
} from "./schemas";
import type { Task, TaskWithMeta } from "@/types/database";

export async function createTask(input: Record<string, unknown>) {
  const session = await auth();
  if (!session?.user?.id) throw new Error("Unauthorized");

  const parsed = createTaskSchema.parse(input);

  const supabase = await createClient();

  const { data: maxOrderTask } = await supabase
    .from("tasks")
    .select("sort_order")
    .eq("project_id", parsed.projectId)
    .eq("status", parsed.status)
    .order("sort_order", { ascending: false })
    .limit(1)
    .maybeSingle();

  const sortOrder = (maxOrderTask?.sort_order ?? 0) + 1;

  const { data: task, error } = await supabase
    .from("tasks")
    .insert({
      project_id: parsed.projectId,
      parent_task_id: parsed.parentTaskId ?? null,
      title: parsed.title,
      description: parsed.description ?? null,
      status: parsed.status,
      priority: parsed.priority,
      assignee_id: parsed.assigneeId ?? null,
      reporter_id: session.user.id,
      due_date: parsed.dueDate ?? null,
      estimated_hours: parsed.estimatedHours ?? null,
      sort_order: sortOrder,
    })
    .select()
    .single();

  if (error) throw new Error(`Failed to create task: ${error.message}`);

  revalidatePath(`/projects/${parsed.projectId}`);
  return task as Task;
}

export async function updateTask(input: Record<string, unknown>) {
  const session = await auth();
  if (!session?.user?.id) throw new Error("Unauthorized");

  const parsed = updateTaskSchema.parse(input);
  const { id, ...updates } = parsed;

  const supabase = await createClient();
  const { data, error } = await supabase
    .from("tasks")
    .update(updates)
    .eq("id", id)
    .select()
    .single();

  if (error) throw new Error(`Failed to update task: ${error.message}`);

  revalidatePath(`/projects/${data.project_id}`);
  return data as Task;
}

export async function updateTaskStatus(input: Record<string, unknown>) {
  const session = await auth();
  if (!session?.user?.id) throw new Error("Unauthorized");

  const parsed = updateTaskStatusSchema.parse(input);

  const supabase = await createClient();
  const { data, error } = await supabase
    .from("tasks")
    .update({ status: parsed.status, sort_order: parsed.sortOrder ?? 0 })
    .eq("id", parsed.id)
    .select()
    .single();

  if (error) throw new Error(`Failed to update task status: ${error.message}`);

  revalidatePath(`/projects/${data.project_id}`);
  return data as Task;
}

export async function deleteTask(taskId: string, projectId: string) {
  const session = await auth();
  if (!session?.user?.id) throw new Error("Unauthorized");

  const supabase = await createClient();
  const { error } = await supabase.from("tasks").delete().eq("id", taskId);

  if (error) throw new Error(`Failed to delete task: ${error.message}`);

  revalidatePath(`/projects/${projectId}`);
}

export async function getTasks(projectId: string): Promise<TaskWithMeta[]> {
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("tasks")
    .select(`
      *,
      assignee:auth.users!tasks_assignee_id_fkey(id, email),
      reporter:auth.users!tasks_reporter_id_fkey(id, email)
    `)
    .eq("project_id", projectId)
    .is("parent_task_id", null)
    .order("sort_order", { ascending: true });

  if (error) throw new Error(`Failed to fetch tasks: ${error.message}`);
  return (data || []) as unknown as TaskWithMeta[];
}

export async function getMyTasks(): Promise<TaskWithMeta[]> {
  const session = await auth();
  if (!session?.user?.id) return [];

  const supabase = await createClient();
  const { data, error } = await supabase
    .from("tasks")
    .select(`
      *,
      assignee:auth.users!tasks_assignee_id_fkey(id, email),
      reporter:auth.users!tasks_reporter_id_fkey(id, email),
      project:projects(id, name, color)
    `)
    .eq("assignee_id", session.user.id)
    .neq("status", "done")
    .order("due_date", { ascending: true, nullsFirst: false });

  if (error) throw new Error(`Failed to fetch tasks: ${error.message}`);
  return (data || []) as unknown as TaskWithMeta[];
}
