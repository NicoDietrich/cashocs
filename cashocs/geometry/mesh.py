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

"""Module for mesh importing and generation."""

from __future__ import annotations

import configparser
import functools
import json
import os
import time
from typing import Any, Callable, Dict, Optional, Union

import fenics
import numpy as np
from typing_extensions import Literal
from typing_extensions import TYPE_CHECKING

from cashocs import _exceptions
from cashocs import _loggers
from cashocs import _utils
from cashocs.geometry import measure
from cashocs.geometry import mesh_quality

if TYPE_CHECKING:
    from cashocs import types


class Mesh(fenics.Mesh):
    """A finite element mesh."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """See base class."""
        super().__init__(*args, **kwargs)
        self._config_flag = False

    def _set_config_flag(self) -> None:
        """Indicates, that the mesh has been loaded via a config file."""
        self._config_flag = True


def _check_imported_mesh_quality(
    input_arg: Union[configparser.ConfigParser, str],
    mesh: Mesh,
    cashocs_remesh_flag: bool,
) -> None:
    """Checks the quality of an imported mesh.

    Args:
        input_arg: The argument used to import the mesh.
        mesh: The finite element mesh whose quality shall be checked.
        cashocs_remesh_flag: A flag, indicating whether remeshing is active.

    """
    if isinstance(input_arg, configparser.ConfigParser):
        mesh_quality_tol_lower = input_arg.getfloat("MeshQuality", "tol_lower")
        mesh_quality_tol_upper = input_arg.getfloat("MeshQuality", "tol_upper")

        if mesh_quality_tol_lower > 0.9 * mesh_quality_tol_upper:
            _loggers.warning(
                "You are using a lower remesh tolerance (tol_lower) close to "
                "the upper one (tol_upper). This may slow down the "
                "optimization considerably."
            )

        mesh_quality_measure = input_arg.get("MeshQuality", "measure")
        mesh_quality_type = input_arg.get("MeshQuality", "type")

        # noinspection PyTypeChecker
        current_mesh_quality = mesh_quality.compute_mesh_quality(
            mesh, mesh_quality_type, mesh_quality_measure
        )

        if not cashocs_remesh_flag:
            if current_mesh_quality < mesh_quality_tol_lower:
                raise _exceptions.InputError(
                    "cashocs.geometry.import_mesh",
                    "input_arg",
                    "The quality of the mesh file you have specified is not "
                    "sufficient for evaluating the cost functional.\n"
                    f"It currently is {current_mesh_quality:.3e} but has to "
                    f"be at least {mesh_quality_tol_lower:.3e}.",
                )

            if current_mesh_quality < mesh_quality_tol_upper:
                raise _exceptions.InputError(
                    "cashocs.geometry.import_mesh",
                    "input_arg",
                    "The quality of the mesh file you have specified is not "
                    "sufficient for computing the shape gradient.\n "
                    + f"It currently is {current_mesh_quality:.3e} but has to "
                    f"be at least {mesh_quality_tol_lower:.3e}.",
                )

        else:
            if current_mesh_quality < mesh_quality_tol_lower:
                raise _exceptions.InputError(
                    "cashocs.geometry.import_mesh",
                    "input_arg",
                    "Remeshing failed.\n"
                    "The quality of the mesh file generated through remeshing is "
                    "not sufficient for evaluating the cost functional.\n"
                    + f"It currently is {current_mesh_quality:.3e} but has to "
                    f"be at least {mesh_quality_tol_lower:.3e}.",
                )

            if current_mesh_quality < mesh_quality_tol_upper:
                raise _exceptions.InputError(
                    "cashocs.geometry.import_mesh",
                    "input_arg",
                    "Remeshing failed.\n"
                    "The quality of the mesh file generated through remeshing "
                    "is not sufficient for computing the shape gradient.\n "
                    + f"It currently is {current_mesh_quality:.3e} but has to "
                    f"be at least {mesh_quality_tol_upper:.3e}.",
                )


def _get_mesh_stats(
    mode: Literal["import", "generate"] = "import"
) -> Callable[..., Callable[..., types.MeshTuple]]:
    """A decorator for mesh importing / generating function which prints stats.

    Args:
        mode: A string indicating whether the mesh is being generated or imported.

    Returns:
        The decorated function.

    """

    def decorator_stats(
        func: Callable[..., types.MeshTuple]
    ) -> Callable[..., types.MeshTuple]:
        """A decorator for a mesh generating function.

        Args:
            func: The function to be decorated.

        Returns:
            The decorated function

        """

        @functools.wraps(func)
        def wrapper_stats(*args: Any, **kwargs: Any) -> types.MeshTuple:
            """Wrapper function for mesh generating functions.

            Args:
                *args: The arguments for the function.
                **kwargs: The keyword arguments for the function.

            Returns:
                The wrapped function.

            """
            word = "importing" if mode.casefold() == "import" else "generating"
            start_time = time.time()
            _loggers.info(f"{word.capitalize()} mesh.")

            value = func(*args, **kwargs)

            end_time = time.time()
            _loggers.info(
                f"Done {word} mesh. Elapsed time: {end_time - start_time:.2f} s."
            )
            _loggers.info(
                f"Mesh contains {value[0].num_vertices():,} vertices and "
                f"{value[0].num_cells():,} cells of type "
                f"{value[0].ufl_cell().cellname()}\n"
            )
            return value

        return wrapper_stats

    return decorator_stats


@_get_mesh_stats(mode="import")
def import_mesh(input_arg: Union[str, configparser.ConfigParser]) -> types.MeshTuple:
    """Imports a mesh file for use with cashocs / FEniCS.

    This function imports a mesh file that was generated by GMSH and converted to
    .xdmf with the command line function :ref:`cashocs-convert <cashocs_convert>`.
    If there are Physical quantities specified in the GMSH file, these are imported
    to the subdomains and boundaries output of this function and can also be directly
    accessed via the measures, e.g., with ``dx(1)``, ``ds(1)``, etc.

    Args:
        input_arg: This is either a string, in which case it corresponds to the location
            of the mesh file in .xdmf file format, or a config file that
            has this path stored in its settings, under the section Mesh, as
            parameter ``mesh_file``.

    Returns:
        A tuple (mesh, subdomains, boundaries, dx, ds, dS), where mesh is the imported
        FEM mesh, subdomains is a mesh function for the subdomains, boundaries is a mesh
        function for the boundaries, dx is a volume measure, ds is a surface measure,
        and dS is a measure for the interior facets.

    Notes:
        In case the boundaries in the Gmsh .msh file are not only marked with numbers
        (as physical groups), but also with names (i.e. strings), these strings can be
        used with the integration measures ``dx`` and ``ds`` returned by this method.
        E.g., if one specified the following in a 2D Gmsh .geo file ::

            Physical Surface("domain", 1) = {i,j,k};

        where i,j,k are representative for some integers, then this can be used in the
        measure ``dx`` (as we are 2D) as follows. The command ::

            dx(1)

        is completely equivalent to ::

           dx("domain")

        and both can be used interchangeably.

    """
    cashocs_remesh_flag, temp_dir = _utils.parse_remesh()

    # Check for the file format
    mesh_file: str = ""
    if isinstance(input_arg, str):
        mesh_file = input_arg
    elif isinstance(input_arg, configparser.ConfigParser):
        if not cashocs_remesh_flag:
            mesh_file = input_arg.get("Mesh", "mesh_file")
        else:
            with open(f"{temp_dir}/temp_dict.json", "r", encoding="utf-8") as file:
                temp_dict: Dict = json.load(file)
            mesh_file = temp_dict["mesh_file"]

    file_string = mesh_file[:-5]

    mesh = Mesh()
    xdmf_file = fenics.XDMFFile(mesh.mpi_comm(), mesh_file)
    xdmf_file.read(mesh)
    xdmf_file.close()

    subdomains_mvc = fenics.MeshValueCollection(
        "size_t", mesh, mesh.geometric_dimension()
    )
    boundaries_mvc = fenics.MeshValueCollection(
        "size_t", mesh, mesh.geometric_dimension() - 1
    )

    if os.path.isfile(f"{file_string}_subdomains.xdmf"):
        xdmf_subdomains = fenics.XDMFFile(
            mesh.mpi_comm(), f"{file_string}_subdomains.xdmf"
        )
        xdmf_subdomains.read(subdomains_mvc, "subdomains")
        xdmf_subdomains.close()
    if os.path.isfile(f"{file_string}_boundaries.xdmf"):
        xdmf_boundaries = fenics.XDMFFile(
            mesh.mpi_comm(), f"{file_string}_boundaries.xdmf"
        )
        xdmf_boundaries.read(boundaries_mvc, "boundaries")
        xdmf_boundaries.close()

    physical_groups: Optional[Dict[str, Dict[str, int]]] = None
    if os.path.isfile(f"{file_string}_physical_groups.json"):
        with open(f"{file_string}_physical_groups.json", "r", encoding="utf-8") as file:
            physical_groups = json.load(file)

    subdomains = fenics.MeshFunction("size_t", mesh, subdomains_mvc)
    boundaries = fenics.MeshFunction("size_t", mesh, boundaries_mvc)

    dx = measure.NamedMeasure(
        "dx", domain=mesh, subdomain_data=subdomains, physical_groups=physical_groups
    )
    ds = measure.NamedMeasure(
        "ds", domain=mesh, subdomain_data=boundaries, physical_groups=physical_groups
    )
    d_interior_facet = measure.NamedMeasure(
        "dS", domain=mesh, subdomain_data=boundaries, physical_groups=physical_groups
    )

    # Add an attribute to the mesh to show with what procedure it was generated
    # noinspection PyProtectedMember
    # pylint: disable=protected-access
    mesh._set_config_flag()
    # Add the physical groups to the mesh in case they are present
    if physical_groups is not None:
        mesh.physical_groups = physical_groups

    # Check the mesh quality of the imported mesh in case a config file is passed
    _check_imported_mesh_quality(input_arg, mesh, cashocs_remesh_flag)

    return mesh, subdomains, boundaries, dx, ds, d_interior_facet


@_get_mesh_stats(mode="generate")
def regular_mesh(
    n: int = 10,
    length_x: float = 1.0,
    length_y: float = 1.0,
    length_z: Optional[float] = None,
    diagonal: Literal["left", "right", "left/right", "right/left", "crossed"] = "right",
) -> types.MeshTuple:
    r"""Creates a mesh corresponding to a rectangle or cube.

    This function creates a uniform mesh of either a rectangle or a cube, starting at
    the origin and having length specified in ``length_x``, ``length_y``, and
    ``length_z``. The resulting mesh uses ``n`` elements along the shortest direction
    and accordingly many along the longer ones. The resulting domain is

    .. math::
        \begin{alignedat}{2}
        &[0, length_x] \times [0, length_y] \quad &&\text{ in } 2D, \\
        &[0, length_x] \times [0, length_y] \times [0, length_z] \quad &&\text{ in } 3D.
        \end{alignedat}

    The boundary markers are ordered as follows:

      - 1 corresponds to :math:`x=0`.

      - 2 corresponds to :math:`x=length_x`.

      - 3 corresponds to :math:`y=0`.

      - 4 corresponds to :math:`y=length_y`.

      - 5 corresponds to :math:`z=0` (only in 3D).

      - 6 corresponds to :math:`z=length_z` (only in 3D).

    Args:
        n: Number of elements in the shortest coordinate direction.
        length_x: Length in x-direction.
        length_y: Length in y-direction.
        length_z: Length in z-direction, if this is ``None``, then the geometry will be
            two-dimensional (default is ``None``).
        diagonal: This defines the type of diagonal used to create the box mesh in 2D.
            This can be one of ``"right"``, ``"left"``, ``"left/right"``,
            ``"right/left"`` or ``"crossed"``.

    Returns:
        A tuple (mesh, subdomains, boundaries, dx, ds, dS), where mesh is the imported
        FEM mesh, subdomains is a mesh function for the subdomains, boundaries is a mesh
        function for the boundaries, dx is a volume measure, ds is a surface measure,
        and dS is a measure for the interior facets.

    """
    if length_x <= 0.0:
        raise _exceptions.InputError(
            "cashocs.geometry.regular_mesh", "length_x", "length_x needs to be positive"
        )
    if length_y <= 0.0:
        raise _exceptions.InputError(
            "cashocs.geometry.regular_mesh", "length_y", "length_y needs to be positive"
        )
    if not (length_z is None or length_z > 0.0):
        raise _exceptions.InputError(
            "cashocs.geometry.regular_mesh",
            "length_z",
            "length_z needs to be positive or None (for 2D mesh)",
        )

    n = int(n)

    if length_z is None:
        sizes = [length_x, length_y]
        dim = 2
    else:
        sizes = [length_x, length_y, length_z]
        dim = 3

    size_min = np.min(sizes)
    num_points = [int(np.round(length / size_min * n)) for length in sizes]

    if length_z is None:
        mesh = fenics.RectangleMesh(
            fenics.Point(0, 0),
            fenics.Point(sizes),
            num_points[0],
            num_points[1],
            diagonal=diagonal,
        )
    else:
        mesh = fenics.BoxMesh(
            fenics.Point(0, 0, 0),
            fenics.Point(sizes),
            num_points[0],
            num_points[1],
            num_points[2],
        )

    subdomains = fenics.MeshFunction("size_t", mesh, dim=dim)
    boundaries = fenics.MeshFunction("size_t", mesh, dim=dim - 1)

    x_min = fenics.CompiledSubDomain(
        "on_boundary && near(x[0], 0, tol)", tol=fenics.DOLFIN_EPS
    )
    x_max = fenics.CompiledSubDomain(
        "on_boundary && near(x[0], length, tol)", tol=fenics.DOLFIN_EPS, length=sizes[0]
    )
    x_min.mark(boundaries, 1)
    x_max.mark(boundaries, 2)

    y_min = fenics.CompiledSubDomain(
        "on_boundary && near(x[1], 0, tol)", tol=fenics.DOLFIN_EPS
    )
    y_max = fenics.CompiledSubDomain(
        "on_boundary && near(x[1], length, tol)", tol=fenics.DOLFIN_EPS, length=sizes[1]
    )
    y_min.mark(boundaries, 3)
    y_max.mark(boundaries, 4)

    if length_z is not None:
        z_min = fenics.CompiledSubDomain(
            "on_boundary && near(x[2], 0, tol)", tol=fenics.DOLFIN_EPS
        )
        z_max = fenics.CompiledSubDomain(
            "on_boundary && near(x[2], length, tol)",
            tol=fenics.DOLFIN_EPS,
            length=sizes[2],
        )
        z_min.mark(boundaries, 5)
        z_max.mark(boundaries, 6)

    dx = measure.NamedMeasure("dx", mesh, subdomain_data=subdomains)
    ds = measure.NamedMeasure("ds", mesh, subdomain_data=boundaries)
    d_interior_facet = measure.NamedMeasure("dS", mesh)

    return mesh, subdomains, boundaries, dx, ds, d_interior_facet


@_get_mesh_stats(mode="generate")
def regular_box_mesh(
    n: int = 10,
    start_x: float = 0.0,
    start_y: float = 0.0,
    start_z: Optional[float] = None,
    end_x: float = 1.0,
    end_y: float = 1.0,
    end_z: Optional[float] = None,
    diagonal: Literal["right", "left", "left/right", "right/left", "crossed"] = "right",
) -> types.MeshTuple:
    r"""Creates a mesh corresponding to a rectangle or cube.

    This function creates a uniform mesh of either a rectangle
    or a cube, with specified start (``S_``) and end points (``E_``).
    The resulting mesh uses ``n`` elements along the shortest direction
    and accordingly many along the longer ones. The resulting domain is

    .. math::
        \begin{alignedat}{2}
            &[start_x, end_x] \times [start_y, end_y] \quad &&\text{ in } 2D, \\
            &[start_x, end_x] \times [start_y, end_y] \times [start_z, end_z] \quad
            &&\text{ in } 3D.
        \end{alignedat}

    The boundary markers are ordered as follows:

      - 1 corresponds to :math:`x=start_x`.

      - 2 corresponds to :math:`x=end_x`.

      - 3 corresponds to :math:`y=start_y`.

      - 4 corresponds to :math:`y=end_y`.

      - 5 corresponds to :math:`z=start_z` (only in 3D).

      - 6 corresponds to :math:`z=end_z` (only in 3D).

    Args:
        n: Number of elements in the shortest coordinate direction.
        start_x: Start of the x-interval.
        start_y: Start of the y-interval.
        start_z: Start of the z-interval, mesh is 2D if this is ``None`` (default is
            ``None``).
        end_x: End of the x-interval.
        end_y: End of the y-interval.
        end_z: End of the z-interval, mesh is 2D if this is ``None`` (default is
            ``None``).
        diagonal: This defines the type of diagonal used to create the box mesh in 2D.
            This can be one of ``"right"``, ``"left"``, ``"left/right"``,
            ``"right/left"`` or ``"crossed"``.

    Returns:
        A tuple (mesh, subdomains, boundaries, dx, ds, dS), where mesh is the imported
        FEM mesh, subdomains is a mesh function for the subdomains, boundaries is a mesh
        function for the boundaries, dx is a volume measure, ds is a surface measure,
        and dS is a measure for the interior facets.

    """
    n = int(n)

    if start_x >= end_x:
        raise _exceptions.InputError(
            "cashocs.geometry.regular_box_mesh",
            "start_x",
            "Incorrect input for the x-coordinate. "
            "start_x has to be smaller than end_x.",
        )
    if start_y >= end_y:
        raise _exceptions.InputError(
            "cashocs.geometry.regular_box_mesh",
            "start_y",
            "Incorrect input for the y-coordinate. "
            "start_y has to be smaller than end_y.",
        )

    fail_z = False
    dim = 2
    sizes = [1.0, 1.0]

    if start_z is None and end_z is None:
        lx = end_x - start_x
        ly = end_y - start_y
        sizes = [lx, ly]
        dim = 2
    else:
        if start_z is not None and end_z is not None:
            if start_z >= end_z:
                fail_z = True
            else:
                lx = end_x - start_x
                ly = end_y - start_y
                # noinspection PyTypeChecker
                lz = end_z - start_z
                sizes = [lx, ly, lz]
                dim = 3

        elif start_z is None and end_z is not None:
            fail_z = True
        else:
            fail_z = True

    if fail_z:
        raise _exceptions.InputError(
            "cashocs.geometry.regular_box_mesh",
            "start_z",
            "Incorrect input for the z-coordinate. "
            "start_z has to be smaller than end_z, "
            "or only one of them is specified.",
        )

    size_min = np.min(sizes)
    num_points = [int(np.round(length / size_min * n)) for length in sizes]

    if start_z is None:
        mesh = fenics.RectangleMesh(
            fenics.Point(start_x, start_y),
            fenics.Point(end_x, end_y),
            num_points[0],
            num_points[1],
            diagonal=diagonal,
        )
    else:
        mesh = fenics.BoxMesh(
            fenics.Point(start_x, start_y, start_z),
            fenics.Point(end_x, end_y, end_z),
            num_points[0],
            num_points[1],
            num_points[2],
        )

    subdomains = fenics.MeshFunction("size_t", mesh, dim=dim)
    boundaries = fenics.MeshFunction("size_t", mesh, dim=dim - 1)

    x_min = fenics.CompiledSubDomain(
        "on_boundary && near(x[0], sx, tol)", tol=fenics.DOLFIN_EPS, sx=start_x
    )
    x_max = fenics.CompiledSubDomain(
        "on_boundary && near(x[0], ex, tol)", tol=fenics.DOLFIN_EPS, ex=end_x
    )
    x_min.mark(boundaries, 1)
    x_max.mark(boundaries, 2)

    y_min = fenics.CompiledSubDomain(
        "on_boundary && near(x[1], sy, tol)", tol=fenics.DOLFIN_EPS, sy=start_y
    )
    y_max = fenics.CompiledSubDomain(
        "on_boundary && near(x[1], ey, tol)", tol=fenics.DOLFIN_EPS, ey=end_y
    )
    y_min.mark(boundaries, 3)
    y_max.mark(boundaries, 4)

    if start_z is not None:
        z_min = fenics.CompiledSubDomain(
            "on_boundary && near(x[2], sz, tol)", tol=fenics.DOLFIN_EPS, sz=start_z
        )
        z_max = fenics.CompiledSubDomain(
            "on_boundary && near(x[2], ez, tol)", tol=fenics.DOLFIN_EPS, ez=end_z
        )
        z_min.mark(boundaries, 5)
        z_max.mark(boundaries, 6)

    dx = measure.NamedMeasure("dx", mesh, subdomain_data=subdomains)
    ds = measure.NamedMeasure("ds", mesh, subdomain_data=boundaries)
    d_interior_facet = measure.NamedMeasure("dS", mesh)

    return mesh, subdomains, boundaries, dx, ds, d_interior_facet
