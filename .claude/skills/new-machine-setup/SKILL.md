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

`calc()` already keeps PySCF scratch on disk (`~/.cache/esp-scratch`). If `/tmp` is a small tmpfs
(`df -h /tmp`; WSL often makes it RAM-backed), also point PySCF's global scratch at the disk, for direct
PySCF calls outside `calc()` (sanity-script reference runs):

```bash
echo "TMPDIR = '/var/tmp'" > ~/.pyscf_conf.py
```
The current laptop differs (root-only WSL, venv at `/root/esp-venv`): see CLAUDE.md "This machine".
