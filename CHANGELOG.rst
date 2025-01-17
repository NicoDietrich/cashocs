Change Log
==========

This is cashocs' change log. Note, that only major and minor releases are covered
here as they add new functionality or might change the API. For a documentation
of the maintenance releases, please take a look at
`<https://github.com/sblauth/cashocs/releases>`_.


in development
--------------

* Added the possibility to define additional constraints for the optimization problems as well as solvers which can be used to solve these new problems. This includes Augmented Lagrangian and Quadratic Penalty methods.

* Added the possibility for users to execute their own code before each solution of the state system or after each computation of the gradient with the help of :py:meth:`inject_pre_hook <cashocs.optimization_problem.OptimizationProblem.inject_pre_hook>` and :py:meth:`inject_post_hook <cashocs.optimization_problem.OptimizationProblem.inject_post_hook>`.


1.5.0 (December 22, 2021)
-------------------------

* Major performance increase (particularly for large problems)

* Added support for using the p-Laplacian to compute the shape gradient. 

* cashocs now also imports Gmsh Physical Group information when it is given by strings, which can be used in integration measures (e.g., ``dx('part1')`` or ``ds('inlet')``, or for creating Dirichlet boundary conditions (e.g. ``cashocs.create_dirichlet_bcs(V, Constant(0.0), boundaries, 'dirichlet_boundary')``).

* The nonlinear solver (Newton's method) got an additional ``inexact`` parameter, which allows users to use an inexact Newton's method with iterative solvers. Additionally, users can specify their own Jacobians to be used in Newton's method with the parameter ``dF``.

* Users can now specify the weight of the scalar tracking terms individually (this is now documented).

* New configuration file parameters:

  * Section ShapeGradient

    * ``use_p_laplacian`` is a boolean flag which enables the use of the p-Laplacian for the computation of the shape gradient
    
    * ``p_laplacian_power`` is an integer parameter specifying the power p used for the p-Laplacian

    * ``p_laplacian_stabilization`` is a float parameter, which acts as stabilization term for the p-Laplacian. This should be positive and small (e.g. 1e-3).

    * ``update_inhomogeneous`` is a boolean parameter, which allows to update the cell volume when using ``inhomogeneous=True`` in the ShapeGradient section. This makes small elements have a higher stiffness and updates this over the course of the optimization. Default is ``False``

1.4.0 (September 3, 2021)
-------------------------

* Added the possibility to compute the stiffness for the shape gradient based on the distance to the boundary using the eikonal equation


* Cashocs now supports the tracking of scalar quantities, which are given as integrals of the states / controls / geometric properties. Input parameter is ``scalar_tracking_forms``, which is a dictionary consisting of ``'integrand'``, which is the integrand of the scalar quantity, and ``'tracking_goal'``, which is the (scalar) value that shall be achieved. This feature is documented at `<https://cashocs.readthedocs.io/en/latest/demos/shape_optimization/doc_eikonal_stiffness.html>`_.

* Fixed a bug concerning cashocs' memory management, which would occur if several OptimizationProblems were created one after the other

* Changed the coding style to "black"

* Switched printing to f-string syntax for better readability

* Config files are now copied when they are passed to OptimizationProblems, so that manipulation of them is only possible before the instance is created

* New configuration file parameters:

  * Section ShapeGradient

    * ``use_distance_mu`` is a boolean flag which enables stiffness computation based on distances

    * ``dist_min`` and ``dist_max`` describe the minimal and maximum distance to the boundary for which a certain stiffness is used (see below)

    * ``mu_min`` and ``mu_max`` describe the stiffness values: If the boundary distance is smaller than ``dist_min``, then ``mu = mu_min`` and if the distance is larger than ``dist_max``, we have ``mu = mu_max``

    * ``smooth_mu`` is a boolean flag, which determines how ``mu`` is interpolated between ``dist_min`` and ``dist_max``: If this is set to ``False``, linear interpolation is used, otherwise, a cubic spline is used

    * ``boundaries_dist`` is a list of boundary indices to which the distance shall be computed

* Small bugfixes and other improvements:

  * Switched to pseudo random numbers for the tests for the sake of reproduceability

  * fixed some tolerances for the tests

  * replaced os.system() calls by subprocess.run()


1.3.0 (June 11, 2021)
---------------------


* Improved the remeshing workflow and fixed several smaller bugs concerning it

* New configuration file parameters:

  * Section Output
    
    * ``save_pvd_adjoint`` is a boolean flag which allows users to also save adjoint states in paraview format

    * ``save_pvd_gradient`` is a boolean flag which allows users to save the (shape) gradient(s) in paraview format

    * ``save_txt`` is a boolean flag, which allows users to capture the command line output as .txt file


1.2.0 (December 01, 2020)
-------------------------


* Users can now supply their own bilinear form (or scalar product) for the computation of the shape gradient, which is then used instead of the linear elasticity formulation. This is documented at `<https://cashocs.readthedocs.io/en/latest/demos/shape_optimization/doc_custom_scalar_product.html>`_.

* Added a curvature regularization term for shape optimization, which can be enabled via the config files, similarly to already implemented regularizations. This is documented at `<https://cashocs.readthedocs.io/en/latest/demos/shape_optimization/doc_regularization.html>`_.

* cashocs can now scale individual terms of the cost functional if this is desired. This allows for a more granular handling of problems with cost functionals consisting of multiple terms. This also extends to the regularizations for shape optimization, see `<https://cashocs.readthedocs.io/en/latest/demos/shape_optimization/doc_regularization.html>`_. This feature is documented at `<https://cashocs.readthedocs.io/en/latest/demos/shape_optimization/doc_scaling.html>`_.

* cashocs now uses the logging module to issue messages for the user. The level of verbosity can be controlled via :py:func:`cashocs.set_log_level`.

* New configuration file parameters:

  * Section Regularization:

    * ``factor_curvature`` can be used to specify the weight for the curvature regularization term.

    * ``use_relative_weights`` is a boolean which specifies, whether the weights should be used as scaling factor in front of the regularization terms (if this is ``False``), or whether they should be used to scale the regularization terms so that they have the prescribed value on the initial iteration (if this is ``True``).


1.1.0 (November 13, 2020)
-------------------------


* Added the functionality for cashocs to be used as a solver only, where users can specify their custom adjoint equations and (shape) derivatives for the optimization problems. This is documented at `<https://cashocs.readthedocs.io/en/latest/demos/cashocs_as_solver/solver_index.html>`_.

* Using ``cashocs.create_config`` is deprecated and replaced by ``cashocs.load_config``, but the former will still be supported.

* Configuration files are now not strictly necessary, but still very strongly recommended.

* New configuration file parameters:

  * Section Output:

    * ``result_dir`` can be used to specify where cashocs' output files should be placed.


1.0.0 (September 18, 2020)
--------------------------


* Initial release of cashocs.


