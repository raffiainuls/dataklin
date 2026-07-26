with open("frontend/app/datasets/[id]/page.tsx", "r") as f:
    lines = f.read().splitlines()

for i, line in enumerate(lines):
    if 'Atur Rule Sekarang' in line and '<TabsContent value="clusters"' in lines[i+1]:
        lines[i] = '                    Atur Rule Sekarang\n                  </Button>\n                </div>\n              )}\n            </CardContent>\n          </Card>\n        </TabsContent>'
        break

with open("frontend/app/datasets/[id]/page.tsx", "w") as f:
    f.write('\n'.join(lines))
