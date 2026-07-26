with open("frontend/app/datasets/[id]/page.tsx", "r") as f:
    content = f.read()

import re
old = """  Atur Rule Sekarang
</Button>
                </div>
        <TabsContent value="clusters" className="mt-4">"""

new = """  Atur Rule Sekarang
</Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="clusters" className="mt-4">"""

content = content.replace(old, new)
with open("frontend/app/datasets/[id]/page.tsx", "w") as f:
    f.write(content)
