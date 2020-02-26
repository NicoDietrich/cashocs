"""
Created on 24/02/2020, 13.11

@author: blauths
"""

import fenics
import numpy as np
from ..optimization_algorithm import OptimizationAlgorithm
from _collections import deque



class LBFGS(OptimizationAlgorithm):
	
	def __init__(self, optimization_problem):
		"""Implements the L-BFGS method for solving the optimization problem
		
		Parameters
		----------
		optimization_problem : adpack.optimization.optimization_problem.OptimizationProblem
			instance of the OptimizationProblem (user defined)
		"""
		
		OptimizationAlgorithm.__init__(self, optimization_problem)
		
		self.gradient_problem = self.optimization_problem.gradient_problem
		
		self.gradient = self.optimization_problem.gradient
		self.control = self.optimization_problem.control
		
		self.control_temp = fenics.Function(self.optimization_problem.control_space)
		
		self.cost_functional = self.optimization_problem.reduced_cost_functional
		
		self.stepsize = self.config.getfloat('OptimizationRoutine', 'step_initial')
		self.armijo_stepsize_initial = self.stepsize
		
		self.q = fenics.Function(self.optimization_problem.control_space)
		
		self.verbose = self.config.getboolean('OptimizationRoutine', 'verbose')
		self.tolerance = self.config.getfloat('OptimizationRoutine', 'tolerance')
		self.epsilon_armijo = self.config.getfloat('OptimizationRoutine', 'epsilon_armijo')
		self.beta_armijo = self.config.getfloat('OptimizationRoutine', 'beta_armijo')
		self.maximum_iterations = self.config.getint('OptimizationRoutine', 'maximum_iterations')
		self.memory_vectors = self.config.getint('OptimizationRoutine', 'memory_vectors')
		self.use_bfgs_scaling = self.config.getboolean('OptimizationRoutine', 'use_bfgs_scaling')
		
		if self.memory_vectors > 0:
			self.history_s = deque()
			self.history_y = deque()
			self.history_rho = deque()
			self.gradient_prev = fenics.Function(self.optimization_problem.control_space)
			self.y_k = fenics.Function(self.optimization_problem.control_space)
			self.s_k = fenics.Function(self.optimization_problem.control_space)
		
		self.armijo_broken = False
	
	
	
	def print_results(self):
		"""Prints the current state of the optimization algorithm to the console.
		
		Returns
		-------
		None
			see method description

		"""
		
		if self.iteration == 0:
			output = 'Iteration ' + format(self.iteration, '4d') + ' - Objective value:  ' + format(self.objective_value, '.3e') + \
					 '    Gradient norm:  ' + format(self.gradient_norm_initial, '.3e') + ' (abs)    Step size:  ' + format(self.stepsize, '.3e') + ' \n '
		else:
			output = 'Iteration ' + format(self.iteration, '4d') + ' - Objective value:  ' + format(self.objective_value, '.3e') + \
					 '    Gradient norm:  ' + format(self.relative_norm, '.3e') + ' (rel)    Step size:  ' + format(self.stepsize, '.3e')
		
		if self.verbose:
			print(output)
	
	
	
	def bfgs_scalar_product(self, a, b):
		"""A short cut for computing the scalar product in the BFGS double loop
		
		Parameters
		----------
		a : dolfin.function.function.Function
			first input
		b : dolfin.function.function.Function
			second input
			
		Returns
		-------
		 : float
			the value of the scalar product

		"""
		
		return fenics.assemble(fenics.inner(a, b)*self.optimization_problem.control_measure)
	
	
	
	def compute_search_direction(self, grad):
		"""Computes the search direction for the BFGS method with the so-called double loop
		
		Parameters
		----------
		grad : dolfin.function.function.Function
			the current gradient

		Returns
		-------
		self.q : dolfin.function.function.Function
			a function corresponding to the current / next search direction

		"""
		
		if self.memory_vectors > 0 and len(self.history_s) > 0:
			history_alpha = deque()
			self.q.vector()[:] = grad.vector()[:]
			for i, _ in enumerate(self.history_s):
				alpha = self.history_rho[i]*self.bfgs_scalar_product(self.history_s[i], self.q)
				history_alpha.append(alpha)
				self.q.vector()[:] -= alpha*self.history_y[i].vector()[:]
			
			if self.use_bfgs_scaling and self.iteration > 0:
				factor = self.bfgs_scalar_product(self.history_y[0], self.history_s[0])/self.bfgs_scalar_product(self.history_y[0], self.history_y[0])
			else:
				factor = 1.0
			
			self.q.vector()[:] *= factor
			
			for i, _ in enumerate(self.history_s):
				beta = self.history_rho[-1 - i]*self.bfgs_scalar_product(self.history_y[-1 - i], self.q)
				self.q.vector()[:] += self.history_s[-1 - i].vector()[:]*(history_alpha[-1 - i] - beta)
			
			self.q.vector()[:] *= -1
		
		else:
			self.q.vector()[:] = - grad.vector()[:]
		
		return self.q
	
	
	
	def run(self):
		"""Performs the optimization via the limited memory BFGS method
		
		Returns
		-------
		None
			the result can be found in the control (user defined)

		"""
		
		self.iteration = 0
		self.objective_value = self.cost_functional.compute()
		
		self.gradient_problem.has_solution = False
		self.gradient_problem.solve()
		self.gradient_norm_squared = self.gradient_problem.return_norm_squared()
		self.gradient_norm_initial = np.sqrt(self.gradient_norm_squared)
		self.gradient_norm_inf = np.max(np.abs(self.gradient.vector()[:]))
		
		self.relative_norm = 1.0
		
		self.print_results()
		
		while self.relative_norm > self.tolerance:
			self.control_temp.vector()[:] = self.control.vector()[:]
			self.search_direction = self.compute_search_direction(self.gradient)
			self.search_direction_inf = np.max(np.abs(self.search_direction.vector()[:]))
			
			self.directional_derivative = self.bfgs_scalar_product(self.search_direction, self.gradient)

			# Armijo Line Search
			while True:
				if self.stepsize*self.search_direction_inf <= 1e-10:
					self.armijo_broken = True
					break
				elif self.memory_vectors == 0 and self.iteration > 0 and self.stepsize/self.armijo_stepsize_initial <= 1e-8:
					self.armijo_broken = True
					break
				
				self.control.vector()[:] += self.stepsize*self.search_direction.vector()[:]
				
				self.state_problem.has_solution = False
				self.objective_step = self.cost_functional.compute()
				
				if self.objective_step < self.objective_value + self.epsilon_armijo*self.stepsize*self.directional_derivative:
					if self.iteration == 0:
						self.armijo_stepsize_initial = self.stepsize
					break
					
				else:
					self.stepsize /= self.beta_armijo
					self.control.vector()[:] = self.control_temp.vector()[:]
				
			
			if self.armijo_broken:
				print('Armijo rule failed')
				break
			
			self.objective_value = self.objective_step
			
			if self.memory_vectors > 0:
				self.gradient_prev.vector()[:] = self.gradient.vector()[:]
			
			self.adjoint_problem.has_solution = False
			self.gradient_problem.has_solution = False
			self.gradient_problem.solve()
			
			self.gradient_norm_squared = self.gradient_problem.return_norm_squared()
			self.relative_norm = np.sqrt(self.gradient_norm_squared) / self.gradient_norm_initial
			self.gradient_norm_inf = np.max(np.abs(self.gradient.vector()[:]))
			
			if self.memory_vectors > 0:
				self.y_k.vector()[:] = self.gradient.vector()[:] - self.gradient_prev.vector()[:]
				self.s_k.vector()[:] = self.stepsize*self.search_direction.vector()[:]
				self.history_y.appendleft(self.y_k.copy(True))
				self.history_s.appendleft(self.s_k.copy(True))
				rho = 1/self.bfgs_scalar_product(self.y_k, self.s_k)
				self.history_rho.appendleft(rho)
				
				if 1/rho <= 0:
					self.history_s = deque()
					self.history_y = deque()
					self.history_rho = deque()
				
				if len(self.history_s) > self.memory_vectors:
					self.history_s.pop()
					self.history_y.pop()
					self.history_rho.pop()
			
			self.iteration += 1
			self.print_results()
			
			if self.iteration >= self.maximum_iterations:
				break
			
			self.stepsize *= self.beta_armijo
			
		print('')
		print('Statistics --- Total iterations: ' + format(self.iteration, '4d') + ' --- Final objective value:  ' + format(self.objective_value, '.3e') +
			  ' --- Final gradient norm:  ' + format(self.relative_norm, '.3e') + ' (rel)')
		print('           --- State equations solved: ' + str(self.state_problem.number_of_solves) +
			  ' --- Adjoint equations solved: ' + str(self.adjoint_problem.number_of_solves))
		print('')
