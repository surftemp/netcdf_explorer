import os
import json
names = []
for name in os.listdir("./cmaps"):
    print(name)
    if name.endswith(".json"):
         names.append(os.path.splitext(name)[0])
print(json.dumps(names))
