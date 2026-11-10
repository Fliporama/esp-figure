import sys, numpy as np, pyvista as pv
from matplotlib.colors import LinearSegmentedColormap
pv.OFF_SCREEN = True
B2A = 0.529177

def read_cube(fn):
    L = open(fn).read().split("\n")
    n, *o = L[2].split(); n = int(n); o = np.array(o[:3], float)
    ax = [L[3+i].split() for i in range(3)]
    shape = [int(a[0]) for a in ax]; vec = np.array([a[1:4] for a in ax], float)
    atoms = [L[6+i].split() for i in range(n)]
    data = np.array(" ".join(L[6+n:]).split(), float).reshape(shape)
    g = pv.ImageData(dimensions=shape, spacing=np.diag(vec)*B2A, origin=o*B2A)
    g.point_data["v"] = data.flatten(order="F")
    xyz = np.array([a[2:5] for a in atoms], float)*B2A
    Z = [int(a[0]) for a in atoms]
    return g, Z, xyz

