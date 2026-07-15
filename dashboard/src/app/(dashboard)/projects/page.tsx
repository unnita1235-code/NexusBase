import { getProjects } from "@/modules/projects/actions";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import { Plus, FolderKanban } from "lucide-react";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/utils";
import { PROJECT_STATUS_LABELS } from "@/types/database";
import type { Project } from "@/types/database";

export default async function ProjectsPage() {
  let projects: Project[] = [];
  try {
    projects = await getProjects();
  } catch {
    // No org yet
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Projects</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage and track all your projects
          </p>
        </div>
        <Link href="/projects/new">
          <Button>
            <Plus className="h-4 w-4" />
            New Project
          </Button>
        </Link>
      </div>

      {projects.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <FolderKanban className="h-10 w-10 text-muted-foreground mb-3" />
            <p className="text-sm font-medium">No projects yet</p>
            <p className="text-xs text-muted-foreground mt-1 mb-4">
              Create your first project to get started
            </p>
            <Link href="/projects/new">
              <Button>
                <Plus className="h-4 w-4" />
                Create Project
              </Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((project) => (
            <Link key={project.id} href={`/projects/${project.id}`}>
              <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div
                        className="h-3 w-3 rounded-full"
                        style={{ backgroundColor: project.color }}
                      />
                      <h3 className="font-semibold text-sm">{project.name}</h3>
                    </div>
                    <Badge variant="outline" className="text-xs">
                      {PROJECT_STATUS_LABELS[project.status]}
                    </Badge>
                  </div>
                  {project.description && (
                    <p className="text-xs text-muted-foreground line-clamp-2 mb-3">
                      {project.description}
                    </p>
                  )}
                  <p className="text-xs text-muted-foreground">
                    Created {formatDate(project.created_at)}
                  </p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
