import sys
import os
import subprocess
import traceback

# Set environment variables for more verbose output
os.environ["REFLEX_DEBUG"] = "1"

try:
    # Run reflex compile only, don't run the server
    result = subprocess.run(
        ["python", "-m", "reflex", "compile"],
        capture_output=True,
        text=True,
        check=False
    )
    
    # Save output to files
    with open("reflex_stdout.log", "w") as f:
        f.write(result.stdout)
    
    with open("reflex_stderr.log", "w") as f:
        f.write(result.stderr)
    
    # Print summary
    print(f"Exit code: {result.returncode}")
    if result.returncode != 0:
        print("Error occurred. Check reflex_stderr.log for details.")
    else:
        print("Reflex compiled successfully.")
    
except Exception as e:
    print(f"Error running script: {e}")
    traceback.print_exc() 