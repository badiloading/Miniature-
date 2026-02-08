import os
import subprocess
import shutil

# 🔧 Fix ffmpeg PATH for Railway / nixpacks
FFMPEG_PATHS = [
    "/nix/store",
    "/usr/bin/ffmpeg",
    "/bin/ffmpeg",
]

if not shutil.which("ffmpeg"):
    for root, dirs, files in os.walk("/nix/store"):
        if "ffmpeg" in files:
            ffmpeg_full_path = os.path.join(root, "ffmpeg")
            os.environ["PATH"] += os.pathsep + os.path.dirname(ffmpeg_full_path)
            break

# ✅ Final check
if not shutil.which("ffmpeg"):
    raise RuntimeError("❌ ffmpeg not found. Make sure nixpacks installed it.")

print("✅ ffmpeg found at:", shutil.which("ffmpeg"))
