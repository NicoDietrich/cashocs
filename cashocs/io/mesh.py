# Copyright (C) 2020-2022 Sebastian Blauth
#
# This file is part of cashocs.
#
# cashocs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cashocs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with cashocs.  If not, see <https://www.gnu.org/licenses/>.

"""Module for handling mesh output.

"""

from __future__ import annotations

from pathlib import Path

import fenics
import numpy as np



def write_out_mesh(
    mesh: fenics.Mesh, original_msh_file: str, out_msh_file: str
) -> None:
    """Writes out the current mesh as .msh file.

    This method updates the vertex positions in the ``original_gmsh_file``, the
    topology of the mesh and its connections are the same. The original GMSH
    file is kept, and a new one is generated under ``out_mesh_file``.

    Parameters
    ----------
    mesh : fenics.Mesh
        The mesh object in fenics that should be saved as GMSH file.
    original_msh_file : str
        Path to the original GMSH mesh file of the mesh object, has to
        end with .msh.
    out_msh_file : str
        Path (and name) of the output mesh file, has to end with .msh.

    Returns
    -------
    None

    Notes
    -----
    The method only works with GMSH 4.1 file format. Others might also work,
    but this is not tested or ensured in any way.
    """

    dim = mesh.geometric_dimension()

    if not Path(out_msh_file).parent.is_dir():
        Path(out_msh_file).parent.mkdir(parents=True, exist_ok=True)

    with open(original_msh_file, "r") as old_file, open(out_msh_file, "w") as new_file:

        points = mesh.coordinates()

        node_section = False
        info_section = False
        subnode_counter = 0
        subwrite_counter = 0
        idcs = np.zeros(1, dtype=int)

        for line in old_file:
            if line == "$EndNodes\n":
                node_section = False

            if not node_section:
                new_file.write(line)
            else:
                split_line = line.split(" ")
                if info_section:
                    new_file.write(line)
                    info_section = False
                else:
                    if len(split_line) == 4:
                        num_subnodes = int(split_line[-1][:-1])
                        subnode_counter = 0
                        subwrite_counter = 0
                        idcs = np.zeros(num_subnodes, dtype=int)
                        new_file.write(line)
                    elif len(split_line) == 1:
                        idcs[subnode_counter] = int(split_line[0][:-1]) - 1
                        subnode_counter += 1
                        new_file.write(line)
                    elif len(split_line) == 3:
                        if dim == 2:
                            mod_line = f"{points[idcs[subwrite_counter]][0]:.16f} {points[idcs[subwrite_counter]][1]:.16f} 0\n"
                        elif dim == 3:
                            mod_line = f"{points[idcs[subwrite_counter]][0]:.16f} {points[idcs[subwrite_counter]][1]:.16f} {points[idcs[subwrite_counter]][2]:.16f}\n"

                        new_file.write(mod_line)
                        subwrite_counter += 1

            if line == "$Nodes\n":
                node_section = True
                info_section = True