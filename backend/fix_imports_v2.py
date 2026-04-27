import os

def fix_imports(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    # Core
                    new_content = content.replace("from app.config import", "from app.core.config import")
                    new_content = new_content.replace("from app.shared.encryption import", "from app.core.encryption import")
                    new_content = new_content.replace("from app.shared.audit_logger import", "from app.core.audit_logger import")
                    new_content = new_content.replace("from app.shared.logging_middleware import", "from app.core.logging_middleware import")
                    new_content = new_content.replace("from app.shared.dynamic_config import", "from app.core.dynamic_config import")
                    
                    # Domain
                    new_content = new_content.replace("from app.shared.models import", "from app.domain.rag import")
                    
                    # Infrastructure
                    new_content = new_content.replace("from app.shared.db import", "from app.infrastructure.database import")
                    new_content = new_content.replace("from app.knowledge_graph.neo4j_client import", "from app.infrastructure.neo4j_client import")
                    new_content = new_content.replace("from app.retrieval.semantic_cache import", "from app.infrastructure.redis_cache import")
                    
                    # Agents
                    new_content = new_content.replace("from app.graph.builder import", "from app.agents.workflow import")
                    new_content = new_content.replace("from app.graph.state import", "from app.agents.state import")
                    new_content = new_content.replace("from app.graph.nodes import", "from app.agents.nodes import")
                    new_content = new_content.replace("from app.graph.edges import", "from app.agents.edges import")
                    
                    if new_content != content:
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        print(f"Fixed imports in {path}")
                except Exception as e:
                    print(f"Error processing {path}: {e}")

if __name__ == "__main__":
    base = "app" if os.path.exists("app") else "backend/app"
    fix_imports(base)
