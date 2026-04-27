import os
import shutil

def finalize_move():
    base = "app" if os.path.exists("app") else "backend/app"
    shared_dir = os.path.join(base, "shared")
    core_dir = os.path.join(base, "core")
    infra_dir = os.path.join(base, "infrastructure")
    
    if not os.path.exists(core_dir): os.makedirs(core_dir)
    
    # Move files to core
    for f in ["audit_logger.py", "encryption.py"]:
        src = os.path.join(shared_dir, f)
        dst = os.path.join(core_dir, f)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"Copied {f} to {core_dir}")
            
    # Models are already in domain/rag.py, so we can just update imports
    
if __name__ == "__main__":
    finalize_move()
