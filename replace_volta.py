import os
import re

folder_path = "."

# Real trap regex 😮‍💨 — group(1)=key, group(2)=format args (optional)
pattern = re.compile(
    r"""
    (?<!\w)                # not part of a variable name
    \(?                   # optional opening (
    _\(\s*'([a-zA-Z0-9_]+)'\s*\)  # k.key()
    \)?                   # optional closing )
    (?:\.format\((.*?)\))?  # optional .format(...)
    """,
    re.VERBOSE,
)

def fix_content(content):
    def repl(match):
        key = match.group(1)
        args = match.group(2)
        if args:
            return f"k.{key}({args})"
        else:
            return f"k.{key}()"

    return pattern.sub(repl, content)

# File types we sweepin 🧹
file_exts = [".py", ".html", ".txt", ".js"]

for subdir, _, files in os.walk(folder_path):
    for file in files:
        if any(file.endswith(ext) for ext in file_exts):
            path = os.path.join(subdir, file)

            with open(path, "r", encoding="utf-8") as f:
                original = f.read()

            updated = fix_content(original)

            if original != updated:
                print(f"🛠️ Fixed: {path}")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(updated)

print("🚀💥 ALL cleaned. No `_('...')` left on road — now it’s k.dot or nothin fam 😎🔫")
