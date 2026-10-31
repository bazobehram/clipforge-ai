import os
import subprocess
import tempfile
from PIL import Image

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDGE = os.environ.get("BROWSER_BIN", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
STATIC_DIR = os.path.join(ROOT_DIR, "app", "static")
TMP_DIR = tempfile.gettempdir()
TMP_HTML = os.path.join(TMP_DIR, "cf_icon_prod.html")
TMP_PNG = os.path.join(TMP_DIR, "cf_icon_prod.png")

svg_content = """<!DOCTYPE html>
<html>
<head>
<style>
  * { margin:0; padding:0; box-sizing: border-box; }
  body { width: 512px; height: 512px; overflow: hidden; background: #4f46e5; }
</style>
</head>
<body>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <!-- Background Gradient: Electric Violet -> Royal Purple -> Deep Magenta -->
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#4f46e5" />
      <stop offset="35%" stop-color="#7c3aed" />
      <stop offset="70%" stop-color="#9333ea" />
      <stop offset="100%" stop-color="#ec4899" />
    </linearGradient>

    <!-- Center Radial Glow -->
    <radialGradient id="sunGlow" cx="50%" cy="45%" r="55%">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0.28" />
      <stop offset="50%" stop-color="#ffffff" stop-opacity="0.08" />
      <stop offset="100%" stop-color="#000000" stop-opacity="0.15" />
    </radialGradient>

    <!-- Play Button Face Gradient -->
    <linearGradient id="playFace" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ffffff" />
      <stop offset="100%" stop-color="#f1f5f9" />
    </linearGradient>

    <!-- Drop Shadow for 3D Floating Depth -->
    <filter id="floatShadow" x="-30%" y="-30%" width="160%" height="160%">
      <feDropShadow dx="0" dy="18" stdDeviation="20" flood-color="#1e1b4b" flood-opacity="0.6"/>
    </filter>

    <!-- Sparkle Outer Glow -->
    <filter id="goldGlow" x="-50%" y="-50%" width="200%" height="200%">
      <feDropShadow dx="0" dy="0" stdDeviation="10" flood-color="#fbbf24" flood-opacity="0.8"/>
    </filter>
  </defs>

  <!-- 1. FULL-BLEED 100% BACKGROUND (Covers all 512x512 pixels completely with NO transparent corners) -->
  <rect width="512" height="512" fill="url(#bgGrad)" />
  <rect width="512" height="512" fill="url(#sunGlow)" />

  <!-- 2. MAIN ICON GRAPHIC (Centered in Android Safe Zone) -->
  <g filter="url(#floatShadow)">
    <!-- Bold Smooth Play Triangle with Rounded Corners -->
    <path d="M185 140 C168 130 148 142 148 162 L148 350 C148 370 168 382 185 372 L345 278 C362 268 362 244 345 234 Z" 
          fill="url(#playFace)" />

    <!-- Sleek Diagonal AI Cut / Blade Angle across the play symbol -->
    <path d="M210 152 L330 262 L316 276 L196 166 Z" fill="#a855f7" opacity="0.25"/>

    <!-- Mini Film Reel Perforation Dots along the left spine -->
    <circle cx="172" cy="185" r="8" fill="#818cf8" opacity="0.45"/>
    <circle cx="172" cy="256" r="8" fill="#818cf8" opacity="0.45"/>
    <circle cx="172" cy="327" r="8" fill="#818cf8" opacity="0.45"/>

    <!-- AI Magic Sparkle 1 (Large Glowing Gold Star on Top-Right of Play) -->
    <g filter="url(#goldGlow)">
      <path d="M375 105 Q375 145 415 145 Q375 145 375 185 Q375 145 335 145 Q375 145 375 105 Z" fill="#facc15" />
      <circle cx="375" cy="145" r="5" fill="#ffffff"/>
    </g>

    <!-- AI Magic Sparkle 2 (Crisp White Star at Bottom-Left) -->
    <g>
      <path d="M120 345 Q120 370 145 370 Q120 370 120 395 Q120 370 95 370 Q120 370 120 345 Z" fill="#ffffff" opacity="0.95" />
      <circle cx="120" cy="370" r="3" fill="#fef08a"/>
    </g>

    <!-- AI Magic Sparkle 3 (Tiny Star at Top-Left) -->
    <g>
      <path d="M140 100 Q140 115 155 115 Q140 115 140 130 Q140 115 125 115 Q140 115 140 100 Z" fill="#ffffff" opacity="0.85" />
    </g>
  </g>
</svg>
</body>
</html>
"""

pure_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#4f46e5" />
      <stop offset="35%" stop-color="#7c3aed" />
      <stop offset="70%" stop-color="#9333ea" />
      <stop offset="100%" stop-color="#ec4899" />
    </linearGradient>
    <radialGradient id="sunGlow" cx="50%" cy="45%" r="55%">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0.28" />
      <stop offset="50%" stop-color="#ffffff" stop-opacity="0.08" />
      <stop offset="100%" stop-color="#000000" stop-opacity="0.15" />
    </radialGradient>
    <linearGradient id="playFace" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ffffff" />
      <stop offset="100%" stop-color="#f1f5f9" />
    </linearGradient>
    <filter id="floatShadow" x="-30%" y="-30%" width="160%" height="160%">
      <feDropShadow dx="0" dy="18" stdDeviation="20" flood-color="#1e1b4b" flood-opacity="0.6"/>
    </filter>
    <filter id="goldGlow" x="-50%" y="-50%" width="200%" height="200%">
      <feDropShadow dx="0" dy="0" stdDeviation="10" flood-color="#fbbf24" flood-opacity="0.8"/>
    </filter>
  </defs>
  <rect width="512" height="512" fill="url(#bgGrad)" />
  <rect width="512" height="512" fill="url(#sunGlow)" />
  <g filter="url(#floatShadow)">
    <path d="M185 140 C168 130 148 142 148 162 L148 350 C148 370 168 382 185 372 L345 278 C362 268 362 244 345 234 Z" fill="url(#playFace)" />
    <path d="M210 152 L330 262 L316 276 L196 166 Z" fill="#a855f7" opacity="0.25"/>
    <circle cx="172" cy="185" r="8" fill="#818cf8" opacity="0.45"/>
    <circle cx="172" cy="256" r="8" fill="#818cf8" opacity="0.45"/>
    <circle cx="172" cy="327" r="8" fill="#818cf8" opacity="0.45"/>
    <g filter="url(#goldGlow)">
      <path d="M375 105 Q375 145 415 145 Q375 145 375 185 Q375 145 335 145 Q375 145 375 105 Z" fill="#facc15" />
      <circle cx="375" cy="145" r="5" fill="#ffffff"/>
    </g>
    <g>
      <path d="M120 345 Q120 370 145 370 Q120 370 120 395 Q120 370 95 370 Q120 370 120 345 Z" fill="#ffffff" opacity="0.95" />
      <circle cx="120" cy="370" r="3" fill="#fef08a"/>
    </g>
    <g>
      <path d="M140 100 Q140 115 155 115 Q140 115 140 130 Q140 115 125 115 Q140 115 140 100 Z" fill="#ffffff" opacity="0.85" />
    </g>
  </g>
</svg>"""

with open(TMP_HTML, "w", encoding="utf-8") as f:
    f.write(svg_content)

with open(os.path.join(STATIC_DIR, "icon.svg"), "w", encoding="utf-8") as f:
    f.write(pure_svg)

with open(os.path.join(STATIC_DIR, "icon-maskable.svg"), "w", encoding="utf-8") as f:
    f.write(pure_svg)

if os.path.exists(TMP_PNG):
    try: os.remove(TMP_PNG)
    except: pass

cmd = [
    EDGE,
    "--headless=new",
    "--disable-gpu",
    "--hide-scrollbars",
    "--force-device-scale-factor=1",
    "--window-size=512,512",
    f"--screenshot={TMP_PNG}",
    f"file:///{TMP_HTML.replace(os.sep, '/')}"
]

res = subprocess.run(cmd, capture_output=True, text=True)
if os.path.exists(TMP_PNG):
    img = Image.open(TMP_PNG).convert("RGBA")
    img_512 = img.crop((0, 0, 512, 512))
    
    # 512x512
    img_512.save(os.path.join(STATIC_DIR, "icon-512.png"), "PNG")
    img_512.save(os.path.join(STATIC_DIR, "icon-maskable-512.png"), "PNG")
    img_512.save(os.path.join(STATIC_DIR, "icon-v3-512.png"), "PNG")
    img_512.save(os.path.join(STATIC_DIR, "icon-v3-maskable-512.png"), "PNG")
    
    # 192x192
    img_192 = img_512.resize((192, 192), Image.Resampling.LANCZOS)
    img_192.save(os.path.join(STATIC_DIR, "icon-192.png"), "PNG")
    img_192.save(os.path.join(STATIC_DIR, "icon-maskable-192.png"), "PNG")
    img_192.save(os.path.join(STATIC_DIR, "icon-v3-192.png"), "PNG")
    img_192.save(os.path.join(STATIC_DIR, "icon-v3-maskable-192.png"), "PNG")
    
    # Apple Touch Icon 180x180
    img_180 = img_512.resize((180, 180), Image.Resampling.LANCZOS)
    img_180.save(os.path.join(STATIC_DIR, "apple-touch-icon.png"), "PNG")
    img_180.save(os.path.join(STATIC_DIR, "apple-touch-icon-v3.png"), "PNG")
    
    # Favicon 32x32 & 48x48
    img_32 = img_512.resize((32, 32), Image.Resampling.LANCZOS)
    img_32.save(os.path.join(STATIC_DIR, "favicon.png"), "PNG")
    
    print("[SUCCESS] All icons (including v3) generated successfully in", STATIC_DIR)
else:
    print("[ERROR] Failed to capture screenshot.")
