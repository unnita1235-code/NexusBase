export type UserRole = "admin" | "manager" | "member" | "viewer";
export type MembershipStatus = "pending" | "active" | "revoked";
export type ProjectStatus = "active" | "archived" | "completed";
export type TaskStatus = "todo" | "in_progress" | "in_review" | "done" | "blocked";
export type TaskPriority = "low" | "medium" | "high" | "urgent";
export type PlanTier = "free" | "pro" | "enterprise";

export interface Organization {
  id: string;
  name: string;
  slug: string;
  plan_tier: PlanTier;
  created_at: string;
}

export interface Membership {
  id: string;
  user_id: string;
  org_id: string;
  role: UserRole;
  invited_by: string | null;
  status: MembershipStatus;
  created_at: string;
}

export interface Project {
  id: string;
  org_id: string;
  name: string;
  description: string | null;
  status: ProjectStatus;
  color: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: string;
  project_id: string;
  parent_task_id: string | null;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  assignee_id: string | null;
  reporter_id: string | null;
  due_date: string | null;
  sort_order: number;
  estimated_hours: number | null;
  actual_hours: number | null;
  created_at: string;
  updated_at: string;
}

export interface Comment {
  id: string;
  task_id: string;
  author_id: string;
  parent_id: string | null;
  body: string;
  created_at: string;
}

export interface Notification {
  id: string;
  user_id: string;
  type: string;
  title: string;
  body: string | null;
  entity_type: string | null;
  entity_id: string | null;
  read_at: string | null;
  created_at: string;
}

export interface TaskWithMeta extends Task {
  assignee?: { id: string; email: string } | null;
  reporter?: { id: string; email: string } | null;
  project?: { id: string; name: string; color: string } | null;
  subtasks?: Task[];
  comment_count?: number;
}

export interface ProjectWithMeta extends Project {
  task_count?: number;
  completed_task_count?: number;
  created_by_user?: { id: string; email: string };
}

export const TASK_STATUSES: TaskStatus[] = ["todo", "in_progress", "in_review", "done", "blocked"];
export const TASK_PRIORITIES: TaskPriority[] = ["low", "medium", "high", "urgent"];
export const PROJECT_STATUSES: ProjectStatus[] = ["active", "archived", "completed"];

export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  todo: "To Do",
  in_progress: "In Progress",
  in_review: "In Review",
  done: "Done",
  blocked: "Blocked",
};

export const TASK_PRIORITY_LABELS: Record<TaskPriority, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  urgent: "Urgent",
};

export const PROJECT_STATUS_LABELS: Record<ProjectStatus, string> = {
  active: "Active",
  archived: "Archived",
  completed: "Completed",
};

export const ROLE_LABELS: Record<UserRole, string> = {
  admin: "Admin",
  manager: "Manager",
  member: "Member",
  viewer: "Viewer",
};
