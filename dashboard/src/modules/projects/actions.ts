"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import { auth } from "@/auth";
import { createProjectSchema, updateProjectSchema } from "./schemas";
import { slugify } from "@/lib/utils";
import type { Project } from "@/types/database";

export async function createProject(input: FormData | Record<string, unknown>) {
  const session = await auth();
  if (!session?.user?.id) throw new Error("Unauthorized");
  if (!session.user.orgId) throw new Error("No active organization");

  const data = input instanceof FormData ? Object.fromEntries(input) : input;
  const parsed = createProjectSchema.parse(data);

  const supabase = await createClient();

  const { data: project, error } = await supabase
    .from("projects")
    .insert({
      org_id: session.user.orgId,
      name: parsed.name,
      description: parsed.description ?? null,
      color: parsed.color,
      created_by: session.user.id,
    })
    .select()
    .single();

  if (error) throw new Error(`Failed to create project: ${error.message}`);

  revalidatePath("/projects");
  revalidatePath("/dashboard");
  return project as Project;
}

export async function updateProject(input: Record<string, unknown>) {
  const session = await auth();
  if (!session?.user?.id) throw new Error("Unauthorized");

  const parsed = updateProjectSchema.parse(input);
  const { id, ...updates } = parsed;

  const supabase = await createClient();
  const { data, error } = await supabase
    .from("projects")
    .update(updates)
    .eq("id", id)
    .select()
    .single();

  if (error) throw new Error(`Failed to update project: ${error.message}`);

  revalidatePath("/projects");
  revalidatePath(`/projects/${id}`);
  revalidatePath("/dashboard");
  return data as Project;
}

export async function deleteProject(projectId: string) {
  const session = await auth();
  if (!session?.user?.id) throw new Error("Unauthorized");

  const supabase = await createClient();
  const { error } = await supabase.from("projects").delete().eq("id", projectId);

  if (error) throw new Error(`Failed to delete project: ${error.message}`);

  revalidatePath("/projects");
  revalidatePath("/dashboard");
}

export async function getProjects(): Promise<Project[]> {
  const session = await auth();
  if (!session?.user?.orgId) return [];

  const supabase = await createClient();
  const { data, error } = await supabase
    .from("projects")
    .select("*")
    .eq("org_id", session.user.orgId)
    .order("created_at", { ascending: false });

  if (error) throw new Error(`Failed to fetch projects: ${error.message}`);
  return (data || []) as Project[];
}

export async function getProject(projectId: string): Promise<Project | null> {
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("projects")
    .select("*")
    .eq("id", projectId)
    .maybeSingle();

  if (error) throw new Error(`Failed to fetch project: ${error.message}`);
  return data as Project | null;
}
