import json

import matplotlib.cm as cm
import os

folder = "cmaps"

if __name__ == "__main__":

    os.makedirs(folder,exist_ok=True)
    for name in dir(cm):
        cmap = getattr(cm,name)
        if hasattr(cmap, "colors") and isinstance(cmap.colors,list):
            print(name,len(cmap.colors))
            with open(os.path.join(folder,name+".json"),"w") as f:
                f.write(json.dumps({"colors":cmap.colors}))
