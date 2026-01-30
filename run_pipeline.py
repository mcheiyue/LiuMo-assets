import subprocess
import sys
import os

def run_script(script_name, args=None):
    script_path = os.path.join("src", script_name)
    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)
    
    print(f"==================================================")
    print(f"Running: {script_name} {' '.join(args) if args else ''}")
    print(f"==================================================")
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_name}: {e}")
        sys.exit(1)

def main():
    print("Starting LiuMo Data Pipeline...")
    
    # 1. Extraction (Source -> Curated)
    run_script("extract.py")
    
    # 2. Formatting (Curated -> Cleaned (Pre-format))
    run_script("format.py")
    
    # 3. Classification (Cleaned -> Cleaned (Classified))
    run_script("classify.py")
    
    # 4. Building DB (Cleaned -> Output)
    run_script("builder.py", ["--type", "lite"])
    
    print("\nPipeline completed successfully!")
    print("Output available in output/core.db")

if __name__ == "__main__":
    main()
