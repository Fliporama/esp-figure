---
name: new-machine-setup
description: Set up this repo on a new Windows machine (WSL, Python venv, PySCF/RDKit/PyVista). Use only when installing the toolchain somewhere new.
---

PySCF does **not** run natively on Windows. On Windows:

1. PowerShell (admin): `wsl --install` → reboot → set up Ubuntu user.
2. VS Code: install the **WSL** extension, then "WSL: Connect to WSL" and open
   the repo folder from inside WSL (`code .` from the Ubuntu terminal works).
3. In the WSL terminal:

```bash
sudo apt update && sudo apt install -y python3-venv python3-pip libgl1 libxrender1
python3 -m venv .venv && source .venv/bin/activate
pip install --prefer-binary pyscf rdkit pyvista vtk matplotlib pillow
```

Offscreen rendering works without a display (a harmless
`bad X server connection` warning may print).

Optional, for `--d3`: `pip install pyscf-dispersion`; `--opt` needs `geometric`.

If `/tmp` is a small tmpfs (`df -h /tmp`; WSL often makes it RAM-backed), point PySCF's scratch at
the disk, or `--freq` on PAM3 dies with "No space left on device" (> 9 GB scratch):

```bash
echo "TMPDIR = '/var/tmp'" > ~/.pyscf_conf.py
```
The current laptop differs (root-only WSL, venv at `/root/esp-venv`): see CLAUDE.md "This machine".
