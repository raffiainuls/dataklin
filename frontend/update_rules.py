import re

with open("../frontend/app/rules/page.tsx", "r") as f:
    content = f.read()

# Replace button loading state
old_btn = '''{nlBusy ? "Menghubungi LLM..." : "✨ Generate Rule dengan AI"}'''
new_btn = '''{nlBusy ? (
                <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ display: "inline-block", width: "12px", height: "12px", border: "2px solid #fff", borderTopColor: "transparent", borderRadius: "50%", animation: "spin 1s linear infinite" }}></span>
                  AI sedang memproses...
                </span>
              ) : "✨ Generate Rule dengan AI"}'''

content = content.replace(old_btn, new_btn)

# Ensure global css has spin animation
with open("../frontend/app/globals.css", "r") as f:
    css_content = f.read()

if "keyframes spin" not in css_content:
    with open("../frontend/app/globals.css", "a") as f:
        f.write('''
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
''')

with open("../frontend/app/rules/page.tsx", "w") as f:
    f.write(content)
