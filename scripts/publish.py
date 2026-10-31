import os
import re
import sys
import subprocess
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION_FILE = os.path.join(ROOT_DIR, "app", "version.py")
INDEX_HTML = os.path.join(ROOT_DIR, "app", "static", "index.html")
APP_JS = os.path.join(ROOT_DIR, "app", "static", "app.js")
SW_JS = os.path.join(ROOT_DIR, "app", "static", "sw.js")

def get_current_version():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        m = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', content)
        if m:
            return m.group(1)
    return "2.4.0"

def bump_patch(version_str):
    parts = version_str.split(".")
    try:
        parts[-1] = str(int(parts[-1]) + 1)
        return ".".join(parts)
    except Exception:
        return f"{version_str}.1"

def update_files(version, build_date, build_id):
    # 1. Update app/version.py
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(f'# ClipForge AI - Version & Build Metadata\n')
        f.write(f'VERSION = "{version}"\n')
        f.write(f'BUILD_DATE = "{build_date}"\n')
        f.write(f'BUILD_ID = "{build_id}"\n')
    print(f"[*] Updated {VERSION_FILE} -> v{version} ({build_id})")

    # 2. Update app/static/index.html
    with open(INDEX_HTML, "r", encoding="utf-8") as f:
        content = f.read()
    content = re.sub(r'style\.css\?v=[^"\'\s>]+', f'style.css?v={build_id}', content)
    content = re.sub(r'app\.js\?v=[^"\'\s>]+', f'app.js?v={build_id}', content)
    content = re.sub(r'manifest\.json\?v=[^"\'\s>]+', f'manifest.json?v={build_id}', content)
    content = re.sub(r'icon-v3-192\.png\?v=[^"\'\s>]+', f'icon-v3-192.png?v={build_id}', content)
    content = re.sub(r'icon-v3-512\.png\?v=[^"\'\s>]+', f'icon-v3-512.png?v={build_id}', content)
    content = re.sub(r'apple-touch-icon-v3\.png\?v=[^"\'\s>]+', f'apple-touch-icon-v3.png?v={build_id}', content)
    content = re.sub(r'icon\.svg\?v=[^"\'\s>]+', f'icon.svg?v={build_id}', content)
    content = re.sub(r'<span id="login-version-badge"[^>]*>[^<]*</span>',
                     f'<span id="login-version-badge" class="text-[10px] text-slate-500 font-mono tracking-wider">v{version} • Build {build_id}</span>', content)
    content = re.sub(r'<span id="version-text">[^<]*</span>',
                     f'<span id="version-text">v{version}</span>', content)
    with open(INDEX_HTML, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[*] Updated {INDEX_HTML} -> v{version}")

    # 3. Update app/static/sw.js
    with open(SW_JS, "r", encoding="utf-8") as f:
        sw_content = f.read()
    sw_content = re.sub(r"const CACHE_NAME = ['\"][^'\"]+['\"];", f"const CACHE_NAME = 'clipforge-{build_id}';", sw_content)
    with open(SW_JS, "w", encoding="utf-8") as f:
        f.write(sw_content)
    print(f"[*] Updated {SW_JS} -> CACHE_NAME 'clipforge-{build_id}'")

    # 4. Update app/static/app.js
    with open(APP_JS, "r", encoding="utf-8") as f:
        app_content = f.read()
    app_content = re.sub(r"const APP_VERSION = ['\"][^'\"]+['\"];", f"const APP_VERSION = '{version}';", app_content)
    app_content = re.sub(r"const APP_BUILD_ID = ['\"][^'\"]+['\"];", f"const APP_BUILD_ID = '{build_id}';", app_content)
    with open(APP_JS, "w", encoding="utf-8") as f:
        f.write(app_content)
    print(f"[*] Updated {APP_JS} -> v{version} ({build_id})")

def deploy_to_remote():
    remote_host = os.environ.get("DEPLOY_SSH_HOST", "")
    remote_dir = os.environ.get("DEPLOY_REMOTE_DIR", "/opt/clipforge")
    container_name = os.environ.get("DEPLOY_CONTAINER_NAME", "clipforge_app")
    if not remote_host:
        print("[*] DEPLOY_SSH_HOST not set; skipping remote SSH deployment.")
        return

    print(f"[*] Deploying to {remote_host} via tar/ssh...")
    ssh_exe = os.environ.get("SSH_EXE", "ssh")
    tar_cmd = (
        f'tar -czf - -C "{ROOT_DIR}" app | "{ssh_exe}" {remote_host} '
        f'"tar -xzf - -C {remote_dir} && docker cp {remote_dir}/app {container_name}:/app/ && docker restart {container_name}"'
    )
    res = subprocess.run(tar_cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print("[!] Deployment failed:", res.stderr)
        sys.exit(1)
    print("[+] Deployed & Docker restarted successfully!")
    if res.stdout:
        print(res.stdout.strip())

def main():
    target_version = None
    deploy = False

    for arg in sys.argv[1:]:
        if arg == "--deploy":
            deploy = True
        elif arg == "--no-deploy":
            deploy = False
        elif not arg.startswith("--"):
            target_version = arg

    current = get_current_version()
    if not target_version:
        version = bump_patch(current)
    else:
        version = target_version

    now = datetime.now()
    build_date = now.strftime("%Y-%m-%d %H:%M")
    build_id = now.strftime("%Y%m%d_%H%M%S")

    print("==================================================")
    print(f" PUBLISHING CLIPFORGE AI: v{version} ({build_id})")
    print("==================================================")

    update_files(version, build_date, build_id)

    if deploy:
        deploy_to_remote()

    print(f"\n[OK] Release v{version} (Build: {build_id}) successfully updated!")

if __name__ == "__main__":
    main()
