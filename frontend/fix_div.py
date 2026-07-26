with open("app/pipelines/[id]/page.tsx", "r") as f:
    lines = f.read().splitlines()

# find line 151 "              </div>"
del lines[150]

with open("app/pipelines/[id]/page.tsx", "w") as f:
    f.write('\n'.join(lines) + '\n')
