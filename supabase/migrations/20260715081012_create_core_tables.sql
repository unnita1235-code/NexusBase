/*
# Create Core Tables for Project Management App

## Overview
This migration creates the foundational schema for a multi-tenant project management
application: organizations, memberships, projects, tasks, task dependencies, comments,
and notifications. All with RLS policies scoped through org membership.

## New Tables
1. organizations — tenant/workspace root
2. memberships — user↔org junction with role
3. projects — belong to orgs
4. tasks — belong to projects, self-ref for subtasks
5. task_dependencies — blocking relationships
6. comments — threaded discussions on tasks
7. notifications — per-user notification feed

## Security
All tables have RLS enabled. Access scoped through is_org_member/is_org_manager helper functions.
*/

-- ── Organizations ──
CREATE TABLE IF NOT EXISTS organizations (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name        text NOT NULL,
    slug        text UNIQUE NOT NULL,
    plan_tier   text NOT NULL DEFAULT 'free' CHECK (plan_tier IN ('free','pro','enterprise')),
    created_at  timestamptz DEFAULT now()
);

ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;

-- ── Memberships ──
CREATE TABLE IF NOT EXISTS memberships (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    org_id      uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role        text NOT NULL DEFAULT 'member' CHECK (role IN ('admin','manager','member','viewer')),
    invited_by  uuid REFERENCES auth.users(id),
    status      text NOT NULL DEFAULT 'active' CHECK (status IN ('pending','active','revoked')),
    created_at  timestamptz DEFAULT now(),
    UNIQUE(user_id, org_id)
);

ALTER TABLE memberships ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_memberships_user_org ON memberships(user_id, org_id);

-- ── Helper functions (after memberships exists) ──
CREATE OR REPLACE FUNCTION is_org_member(check_org_id uuid)
RETURNS boolean AS $$
    SELECT EXISTS (
        SELECT 1 FROM memberships
        WHERE user_id = auth.uid()
        AND org_id = check_org_id
        AND status = 'active'
    );
$$ LANGUAGE sql SECURITY DEFINER STABLE;

CREATE OR REPLACE FUNCTION is_org_manager(check_org_id uuid)
RETURNS boolean AS $$
    SELECT EXISTS (
        SELECT 1 FROM memberships
        WHERE user_id = auth.uid()
        AND org_id = check_org_id
        AND status = 'active'
        AND role IN ('admin', 'manager')
    );
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- ── Projects ──
CREATE TABLE IF NOT EXISTS projects (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name        text NOT NULL,
    description text,
    status      text NOT NULL DEFAULT 'active' CHECK (status IN ('active','archived','completed')),
    color       text DEFAULT '#475569',
    created_by  uuid NOT NULL REFERENCES auth.users(id),
    created_at  timestamptz DEFAULT now(),
    updated_at  timestamptz DEFAULT now()
);

ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_projects_org_status ON projects(org_id, status);

-- ── Tasks ──
CREATE TABLE IF NOT EXISTS tasks (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    parent_task_id  uuid REFERENCES tasks(id) ON DELETE CASCADE,
    title           text NOT NULL,
    description     text,
    status          text NOT NULL DEFAULT 'todo' CHECK (status IN ('todo','in_progress','in_review','done','blocked')),
    priority        text NOT NULL DEFAULT 'medium' CHECK (priority IN ('low','medium','high','urgent')),
    assignee_id     uuid REFERENCES auth.users(id),
    reporter_id     uuid REFERENCES auth.users(id),
    due_date        timestamptz,
    sort_order      integer NOT NULL DEFAULT 0,
    estimated_hours numeric(5,2),
    actual_hours    numeric(5,2) DEFAULT 0,
    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now()
);

ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_tasks_project_status ON tasks(project_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON tasks(assignee_id) WHERE assignee_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date) WHERE due_date IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_sort_order ON tasks(project_id, status, sort_order);

-- ── Task Dependencies ──
CREATE TABLE IF NOT EXISTS task_dependencies (
    task_id        uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    depends_on_id  uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    PRIMARY KEY (task_id, depends_on_id),
    CHECK (task_id != depends_on_id)
);

ALTER TABLE task_dependencies ENABLE ROW LEVEL SECURITY;

-- ── Comments ──
CREATE TABLE IF NOT EXISTS comments (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id     uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    author_id   uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    parent_id   uuid REFERENCES comments(id) ON DELETE CASCADE,
    body        text NOT NULL,
    created_at  timestamptz DEFAULT now()
);

ALTER TABLE comments ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_comments_task_created ON comments(task_id, created_at);

-- ── Notifications ──
CREATE TABLE IF NOT EXISTS notifications (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    type        text NOT NULL,
    title       text NOT NULL,
    body        text,
    entity_type text,
    entity_id   uuid,
    read_at     timestamptz,
    created_at  timestamptz DEFAULT now()
);

ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON notifications(user_id) WHERE read_at IS NULL;

-- ═══════════════════════════════════════════════════════════════
-- RLS POLICIES
-- ═══════════════════════════════════════════════════════════════

-- ── Organizations ──
DROP POLICY IF EXISTS "select_own_orgs" ON organizations;
CREATE POLICY "select_own_orgs" ON organizations FOR SELECT
    TO authenticated USING (is_org_member(id));

DROP POLICY IF EXISTS "update_own_orgs" ON organizations;
CREATE POLICY "update_own_orgs" ON organizations FOR UPDATE
    TO authenticated USING (is_org_member(id) AND is_org_manager(id))
    WITH CHECK (is_org_member(id) AND is_org_manager(id));

DROP POLICY IF EXISTS "insert_orgs" ON organizations;
CREATE POLICY "insert_orgs" ON organizations FOR INSERT
    TO authenticated WITH CHECK (true);

-- ── Memberships ──
DROP POLICY IF EXISTS "select_memberships" ON memberships;
CREATE POLICY "select_memberships" ON memberships FOR SELECT
    TO authenticated USING (is_org_member(org_id));

DROP POLICY IF EXISTS "insert_memberships" ON memberships;
CREATE POLICY "insert_memberships" ON memberships FOR INSERT
    TO authenticated WITH CHECK (is_org_manager(org_id));

DROP POLICY IF EXISTS "update_memberships" ON memberships;
CREATE POLICY "update_memberships" ON memberships FOR UPDATE
    TO authenticated USING (is_org_manager(org_id))
    WITH CHECK (is_org_manager(org_id));

DROP POLICY IF EXISTS "delete_memberships" ON memberships;
CREATE POLICY "delete_memberships" ON memberships FOR DELETE
    TO authenticated USING (is_org_manager(org_id));

-- ── Projects ──
DROP POLICY IF EXISTS "select_projects" ON projects;
CREATE POLICY "select_projects" ON projects FOR SELECT
    TO authenticated USING (is_org_member(org_id));

DROP POLICY IF EXISTS "insert_projects" ON projects;
CREATE POLICY "insert_projects" ON projects FOR INSERT
    TO authenticated WITH CHECK (is_org_manager(org_id));

DROP POLICY IF EXISTS "update_projects" ON projects;
CREATE POLICY "update_projects" ON projects FOR UPDATE
    TO authenticated USING (is_org_manager(org_id))
    WITH CHECK (is_org_manager(org_id));

DROP POLICY IF EXISTS "delete_projects" ON projects;
CREATE POLICY "delete_projects" ON projects FOR DELETE
    TO authenticated USING (
        is_org_manager(org_id) AND (
            SELECT role FROM memberships WHERE user_id = auth.uid() AND org_id = projects.org_id AND status = 'active'
        ) = 'admin'
    );

-- ── Tasks ──
DROP POLICY IF EXISTS "select_tasks" ON tasks;
CREATE POLICY "select_tasks" ON tasks FOR SELECT
    TO authenticated USING (
        is_org_member((SELECT org_id FROM projects WHERE id = tasks.project_id))
    );

DROP POLICY IF EXISTS "insert_tasks" ON tasks;
CREATE POLICY "insert_tasks" ON tasks FOR INSERT
    TO authenticated WITH CHECK (
        is_org_member((SELECT org_id FROM projects WHERE id = tasks.project_id))
    );

DROP POLICY IF EXISTS "update_tasks" ON tasks;
CREATE POLICY "update_tasks" ON tasks FOR UPDATE
    TO authenticated USING (
        is_org_member((SELECT org_id FROM projects WHERE id = tasks.project_id))
    ) WITH CHECK (
        is_org_member((SELECT org_id FROM projects WHERE id = tasks.project_id))
    );

DROP POLICY IF EXISTS "delete_tasks" ON tasks;
CREATE POLICY "delete_tasks" ON tasks FOR DELETE
    TO authenticated USING (
        is_org_member((SELECT org_id FROM projects WHERE id = tasks.project_id))
    );

-- ── Task Dependencies ──
DROP POLICY IF EXISTS "select_task_deps" ON task_dependencies;
CREATE POLICY "select_task_deps" ON task_dependencies FOR SELECT
    TO authenticated USING (
        is_org_member((SELECT p.org_id FROM tasks t JOIN projects p ON t.project_id = p.id WHERE t.id = task_dependencies.task_id))
    );

DROP POLICY IF EXISTS "insert_task_deps" ON task_dependencies;
CREATE POLICY "insert_task_deps" ON task_dependencies FOR INSERT
    TO authenticated WITH CHECK (
        is_org_member((SELECT p.org_id FROM tasks t JOIN projects p ON t.project_id = p.id WHERE t.id = task_dependencies.task_id))
    );

DROP POLICY IF EXISTS "delete_task_deps" ON task_dependencies;
CREATE POLICY "delete_task_deps" ON task_dependencies FOR DELETE
    TO authenticated USING (
        is_org_member((SELECT p.org_id FROM tasks t JOIN projects p ON t.project_id = p.id WHERE t.id = task_dependencies.task_id))
    );

-- ── Comments ──
DROP POLICY IF EXISTS "select_comments" ON comments;
CREATE POLICY "select_comments" ON comments FOR SELECT
    TO authenticated USING (
        is_org_member((SELECT p.org_id FROM tasks t JOIN projects p ON t.project_id = p.id WHERE t.id = comments.task_id))
    );

DROP POLICY IF EXISTS "insert_comments" ON comments;
CREATE POLICY "insert_comments" ON comments FOR INSERT
    TO authenticated WITH CHECK (
        is_org_member((SELECT p.org_id FROM tasks t JOIN projects p ON t.project_id = p.id WHERE t.id = comments.task_id))
    );

DROP POLICY IF EXISTS "update_comments" ON comments;
CREATE POLICY "update_comments" ON comments FOR UPDATE
    TO authenticated USING (auth.uid() = author_id)
    WITH CHECK (auth.uid() = author_id);

DROP POLICY IF EXISTS "delete_comments" ON comments;
CREATE POLICY "delete_comments" ON comments FOR DELETE
    TO authenticated USING (auth.uid() = author_id);

-- ── Notifications ──
DROP POLICY IF EXISTS "select_notifications" ON notifications;
CREATE POLICY "select_notifications" ON notifications FOR SELECT
    TO authenticated USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "update_notifications" ON notifications;
CREATE POLICY "update_notifications" ON notifications FOR UPDATE
    TO authenticated USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "delete_notifications" ON notifications;
CREATE POLICY "delete_notifications" ON notifications FOR DELETE
    TO authenticated USING (auth.uid() = user_id);

-- ═══════════════════════════════════════════════════════════════
-- TRIGGERS: Auto-update updated_at
-- ═══════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_projects_updated_at ON projects;
CREATE TRIGGER trigger_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS trigger_tasks_updated_at ON tasks;
CREATE TRIGGER trigger_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
