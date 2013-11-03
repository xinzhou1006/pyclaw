#!/usr/bin/env python
# encoding: utf-8

"""
2D compressible flow
================================

Solve the Euler equations of compressible fluid dynamics:

.. math::
    \rho_t + (\rho u)_x + (\rho v)_y & = 0 \\
    (\rho u)_t + (\rho u^2 + p)_x + (\rho uv)_y & = 0 \\
    (\rho v)_t + (\rho uv)_x + (\rho v^2 + p)_y & = 0 \\
    E_t + (u (E + p) )_x + (v (E + p))_y & = 0.

Here h is the depth, (u,v) is the velocity, and g is the gravitational constant.
"""
from clawpack import pyclaw
from clawpack import riemann

solver = pyclaw.ClawSolver2D(riemann.euler_4wave_2D)
solver.all_bcs = pyclaw.BC.extrap

domain = pyclaw.Domain([0.,0.],[1.,1.],[200,200])
solution = pyclaw.Solution(solver.num_eqn,domain)
gamma = 1.4
solution.problem_data['gamma']  = gamma

# Set initial data
xx,yy = domain.grid.p_centers
l = xx<0.5; r = xx>=0.5; b = yy<0.5; t = yy>=0.5
solution.q[0,...] = 2.*l*t + 1.*l*b + 1.*r*t + 3.*r*b
solution.q[1,...] = 0.75*t - 0.75*b
solution.q[2,...] = 0.5*l  - 0.5*r
solution.q[3,...] = 0.5*solution.q[0,...]*(solution.q[1,...]**2+solution.q[2,...]**2) + 1./(gamma-1.)

claw = pyclaw.Controller()
claw.tfinal = 0.3
claw.solution = solution
claw.solver = solver

status = claw.run()

#plot_results()

def load_frame(frame_number):
    from clawpack.pyclaw import Solution

    return Solution(frame_number)

def plot_frame(frame):
    import matplotlib.pyplot as plt
    q = frame.q
    x, y = frame.state.grid.c_centers
    plt.pcolormesh(x, y, q[0,...])

def plot_results():
    from clawpack.visclaw import iplot
    ip = iplot.Iplot(load_frame,plot_frame)
    ip.plotloop()