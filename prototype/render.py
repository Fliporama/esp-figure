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

_, Z, xyz = read_cube("dens.cube")
surf = pv.read("surf.vtk")

col = {1: "#f2f2f2", 6: "#7f7f7f", 7: "#1f3fff", 8: "#ff1f1f"}
rad = {1: 0.17, 6: 0.30, 7: 0.30, 8: 0.30}

def molecule(p):
    for z, r in zip(Z, xyz):
        p.add_mesh(pv.Sphere(rad[z], r, theta_resolution=40, phi_resolution=40),
                   color=col[z], smooth_shading=True, specular=0.8, specular_power=40)
    for i in range(len(Z)):
        for j in range(i+1, len(Z)):
            d = np.linalg.norm(xyz[i]-xyz[j])
            if d < (1.2 if 1 in (Z[i], Z[j]) else 1.75):
                mid = (xyz[i]+xyz[j])/2   # two-tone bond, like GaussView
                for a, b, z in ((xyz[i], mid, Z[i]), (mid, xyz[j], Z[j])):
                    p.add_mesh(pv.Cylinder(center=(a+b)/2, direction=b-a, radius=0.08,
                               height=np.linalg.norm(b-a), resolution=30),
                               color=col[z], smooth_shading=True, specular=0.6)

schemes = {  # one convention for both: negative = red
    "rainbow": (LinearSegmentedColormap.from_list("gv", ["#ff0000", "#ffff00", "#00ff00", "#00ffff", "#0000ff"]), 0.06),
    "rwb":     (LinearSegmentedColormap.from_list("rwb", ["#e8413a", "#ffffff", "#3a4fe8"]), 0.03),
}
for name, (cmap, lim) in schemes.items():
    for mode in ("ball", "esp"):
        p = pv.Plotter(off_screen=True, window_size=(1600, 1000))
        p.set_background("white"); p.enable_depth_peeling(20); p.enable_anti_aliasing("ssaa")
        molecule(p)
        if mode == "esp":
            p.add_mesh(surf, scalars="v", cmap=cmap, clim=(-lim, lim), opacity=0.55,
                       smooth_shading=True, specular=0.3, show_scalar_bar=False)
        c = xyz - xyz.mean(0); ev = np.linalg.svd(c)[2]   # look along the thinnest axis, long axis horizontal
        p.view_vector(ev[2], viewup=ev[1]); p.camera.zoom(1.5)
        p.screenshot(f"{name}_{mode}.png")
print("ok", surf.n_points)
