# Copyright (C) 2020 Sebastian Blauth
#
# This file is part of CASHOCS.
#
# CASHOCS is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# CASHOCS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CASHOCS.  If not, see <https://www.gnu.org/licenses/>.

"""
Created on 02/09/2020, 12.03

@author: blauths
"""

import getopt
import sys
import meshio



def convert(argv):
	try:
		opts, args = getopt.getopt(argv, "h", ["help"])
	except getopt.GetoptError:
		usage()
		sys.exit(2)
	
	
	for opt, arg in opts:
		if opt in ('-h', '--help'):
			usage()
			sys.exit()
	# Check that we have two files
	if not (len(args) == 2):
		usage()
		sys.exit(2)
	
	
	inputfile = args[0]
	outputfile = args[1]
	# Check that the inputfile has .msh file format
	if not (inputfile[-4:] == '.msh'):
		print('Error: Cannot use the current file format as input')
		print('')
		usage()
		sys.exit(2)
	
	# Check that the outputfile has .xdmf format
	if outputfile[-5:] == '.xdmf':
		oformat = '.xdmf'
		ostring = outputfile[:-5]
	else:
		print('Error: Cannot use the current file format as output')
		print('')
		usage()
		sys.exit(2)
	
	mesh_collection = meshio.read(inputfile)
	
	points = mesh_collection.points
	cells_dict = mesh_collection.cells_dict
	cell_data_dict = mesh_collection.cell_data_dict

	# Check, whether we have a 2D or 3D mesh:
	keyvals = cells_dict.keys()
	if 'tetra' in keyvals:
		meshdim = 3
	elif 'triangle' in keyvals:
		meshdim = 2
	else:
		print('Error: This is not a valid input mesh.')
		print('')
		usage()
		sys.exit(2)
	
	if meshdim == 2:
		points = points[:, :2]
		xdmf_mesh = meshio.Mesh(points=points, cells={'triangle' : cells_dict['triangle']})
		meshio.write(ostring + '.xdmf', xdmf_mesh)

		if 'gmsh:physical' in cell_data_dict.keys():
			if 'triangle' in cell_data_dict['gmsh:physical'].keys():
				subdomains = meshio.Mesh(points=points, cells={'triangle': cells_dict['triangle']},
										 cell_data={'subdomains': [cell_data_dict['gmsh:physical']['triangle']]})
				meshio.write(ostring + '_subdomains.xdmf', subdomains)

			if 'line' in cell_data_dict['gmsh:physical'].keys():
				xdmf_boundaries = meshio.Mesh(points=points, cells={'line' : cells_dict['line']},
											  cell_data={'boundaries' : [cell_data_dict['gmsh:physical']['line']]})
				meshio.write(ostring + '_boundaries.xdmf', xdmf_boundaries)
	
	elif meshdim == 3:
		xdmf_mesh = meshio.Mesh(points=points, cells={'tetra' : cells_dict['tetra']})
		meshio.write(ostring + '.xdmf', xdmf_mesh)

		if 'gmsh:physical' in cell_data_dict.keys():
			if 'tetra' in cell_data_dict['gmsh:physical'].keys():
				subdomains = meshio.Mesh(points=points, cells={'tetra': cells_dict['tetra']},
										 cell_data={'subdomains': [cell_data_dict['gmsh:physical']['tetra']]})
				meshio.write(ostring + '_subdomains.xdmf', subdomains)

			if 'triangle' in cell_data_dict['gmsh:physical'].keys():
				xdmf_boundaries = meshio.Mesh(points=points, cells={'triangle' : cells_dict['triangle']},
											  cell_data={'boundaries' : [cell_data_dict['gmsh:physical']['triangle']]})
				meshio.write(ostring + '_boundaries.xdmf', xdmf_boundaries)



def usage():
	"Display usage"
	print("""\
Usage: cashocs-convert input.msh output.xdmf

Supported formats
		Input:
		.msh	- Gmsh, version 2.0 or 4.0 file format

		Output:
		.xdmf 	- XDMF file format
""")