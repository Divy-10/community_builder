import re

def update_css():
    file_path = r'd:\sem-6\community_builders\user\static\admin\css\admin_custom.css'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update the import for Outfit font
    content = content.replace(
        "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');",
        "@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');"
    )

    # 2. Update :root variables
    new_root = """:root {
  --univo-primary: #8b5cf6;
  --univo-primary-hover: #a855f7;
  --univo-primary-light: rgba(99, 102, 241, 0.15);
  --univo-dark-blue: rgba(18, 24, 38, 0.6);
  --univo-cyan: #6366f1;
  --univo-bg: #0b0f19;
  --univo-surface: rgba(18, 24, 38, 0.6);
  --univo-border: rgba(255, 255, 255, 0.08);
  --univo-text-main: #f8fafc;
  --univo-text-muted: #94a3b8;
  --univo-text-light: #64748b;
  --univo-success: #10b981;
  --univo-danger: #ef4444;
  --univo-warning: #f59e0b;
  --univo-secondary: rgba(26, 35, 53, 0.8);
  --univo-secondary-hover: rgba(255, 255, 255, 0.1);
  --univo-font: 'Outfit', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --univo-radius: 10px;
  --univo-radius-lg: 16px;
  --univo-shadow: 0 4px 24px -1px rgba(0, 0, 0, 0.2);
  --univo-shadow-hover: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
  
  --bg-color: #0b0f19;
  --surface-color: rgba(18, 24, 38, 0.6);
  --surface-hover: rgba(26, 35, 53, 0.8);
  --border-color: rgba(255, 255, 255, 0.08);
  --text-primary: #f8fafc;
  --text-secondary: #94a3b8;
  --accent-gradient: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
  --accent-color: #8b5cf6;
  --danger-color: #ef4444;
  --success-color: #10b981;
  --glass-blur: blur(12px);
}"""
    content = re.sub(r':root\s*\{[^}]+\}', new_root, content)

    # 3. Add background-image for body
    body_pattern = r'(body\s*\{[^\}]+)background:\s*var\(--univo-bg\)\s*!important;'
    new_body_bg = r'\1background-color: var(--bg-color) !important;\n  background-image: radial-gradient(circle at 15% 50%, rgba(99, 102, 241, 0.15) 0%, transparent 50%), radial-gradient(circle at 85% 30%, rgba(168, 85, 247, 0.15) 0%, transparent 50%) !important;\n  background-attachment: fixed !important;'
    content = re.sub(body_pattern, new_body_bg, content)

    # 4. Update Header styling
    header_pattern = r'(#header\s*\{[^}]+)background:\s*linear-gradient[^;]+;\s*(color:[^}]+)\}'
    new_header = r'\1background: var(--surface-color) !important;\n  backdrop-filter: var(--glass-blur);\n  -webkit-backdrop-filter: var(--glass-blur);\n  border-bottom: 1px solid var(--border-color) !important;\n  \2}'
    content = re.sub(header_pattern, new_header, content)

    # 5. Update Nav Sidebar styling
    nav_pattern = r'(#nav-sidebar\s*\{[^}]+)background:\s*var\(--univo-dark-blue\)[^;]+;'
    new_nav = r'\1background: var(--surface-color) !important;\n  backdrop-filter: var(--glass-blur);\n  -webkit-backdrop-filter: var(--glass-blur);\n  border: 1px solid var(--border-color) !important;'
    content = re.sub(nav_pattern, new_nav, content)

    # 6. Remove solid dark blue backgrounds from modules, h2, captions
    content = re.sub(
        r'background:\s*linear-gradient\(135deg,\s*var\(--univo-dark-blue\)\s*0%,\s*#003366\s*100%\)\s*!important;',
        r'background: var(--univo-primary-light) !important;\n  backdrop-filter: var(--glass-blur);',
        content
    )

    # 7. Button styling updates (gradients instead of solid)
    # primary submits
    content = content.replace(
        "background: var(--univo-primary) !important;\n  color: #FFFFFF !important;",
        "background: var(--accent-gradient) !important;\n  color: #FFFFFF !important;\n  border: none !important;"
    )

    # 8. Fixed hardcoded #5865F2 and #FFFFFF
    content = content.replace("#5865F2", "var(--accent-color)")
    content = content.replace("background: #FFFFFF !important;", "background: transparent !important;")
    content = content.replace("background: #F9FAFB !important;", "background: rgba(255, 255, 255, 0.05) !important;")
    
    # login page specific fixes
    content = content.replace(
        "background: linear-gradient(135deg, var(--univo-dark-blue) 0%, #003366 50%, var(--univo-primary) 100%) !important;",
        "background-color: var(--bg-color) !important;\n  background-image: radial-gradient(circle at 15% 50%, rgba(99, 102, 241, 0.15) 0%, transparent 50%), radial-gradient(circle at 85% 30%, rgba(168, 85, 247, 0.15) 0%, transparent 50%) !important;\n  background-attachment: fixed !important;"
    )

    # Replace Inter with Outfit just in case
    content = content.replace("'Inter'", "'Outfit'")

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    update_css()
    print("CSS updated perfectly.")
