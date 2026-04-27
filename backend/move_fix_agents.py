import os
import shutil

def move_and_fix():
    # Detect directory
    base = "app" if os.path.exists("app") else "backend/app"
    src_dir = os.path.join(base, "graph")
    dst_dir = os.path.join(base, "agents")
    
    print(f"Base dir: {base}")
    
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)
        
    for f in ["nodes.py", "edges.py"]:
        src = os.path.join(src_dir, f)
        dst = os.path.join(dst_dir, f)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"Copied {f} to {dst_dir}")
        else:
            print(f"Source not found: {src}")
            
    # Fix imports in agents/workflow.py
    workflow_path = os.path.join(dst_dir, "workflow.py")
    if os.path.exists(workflow_path):
        with open(workflow_path, "r", encoding="utf-8") as f:
            content = f.read()
        new_content = content.replace("from app.graph.nodes import", "from app.agents.nodes import")
        new_content = new_content.replace("from app.graph.edges import", "from app.agents.edges import")
        with open(workflow_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("Fixed workflow.py imports")

    # Fix imports in agents/nodes.py and agents/edges.py
    for f in ["nodes.py", "edges.py"]:
        path = os.path.join(dst_dir, f)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as file:
                content = file.read()
            new_content = content.replace("from app.graph.state import GraphState", "from app.agents.state import GraphState")
            new_content = new_content.replace("from app.shared.models import", "from app.domain.rag import")
            with open(path, "w", encoding="utf-8") as file:
                file.write(new_content)
            print(f"Fixed imports in agents/{f}")

if __name__ == "__main__":
    move_and_fix()
