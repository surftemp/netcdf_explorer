"""
Export colormaps from Python / matplotlib to JavaScript.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

import json

from matplotlib.colors import Colormap

import matplotlib.cm as cm
import matplotlib.colors as colors
import numpy as np


# -----------------------------------------------------------------------------
# MAIN CODE
# -----------------------------------------------------------------------------

if __name__ == "__main__":

    # Loop over all matplotlib colormaps and store them in a dictionary. This
    # dictionary contains the colors of the colormap as list of lists (= RGB
    # tuples), and whether or not the colormap should be interpolated (= false
    # for qualitative colormaps).
    colormaps = {}
    for name in dir(cm):

        # Skip reversed colormaps (they don't contain additional information)
        if name.endswith("_r"):
            continue

        # If `cmap` is a colormap, we can store the association information
        if isinstance(cmap := getattr(cm, name), Colormap):

            # Evaluate colormap on the grid to get colors, drop alpha channel
            # information, and round to a reasonable precision
            colors = np.around(cmap(np.linspace(0, 1, cmap.N))[:, 0:3], 4)

            # Store relevant colormap information
            colormaps[cmap.name] = {
                "interpolate": cmap.N >= 256,
                "colors": colors.tolist(),
            }

            with open("cmaps/"+cmap.name+".json","w") as f:
                f.write(json.dumps(colors.tolist()))

