#!/usr/bin/env python
# encoding: utf-8

#===========================================================================
# Import libraries
#===========================================================================
import numpy as np
from petsc4py import PETSc
import petclaw


def mapc2p_annulus(grid,mC):
    """
    Specifies the mapping to curvilinear coordinates.

    Takes as input: array_list made by x_coordinates, y_ccordinates in the map 
                    space.
    Returns as output: array_list made by x_coordinates, y_ccordinates in the 
                       physical space.

    Inputs: mC = list composed by two arrays 
                 [array ([xc1, xc2, ...]), array([yc1, yc2, ...])]

    Output: pC = list composed by two arrays 
                 [array ([xp1, xp2, ...]), array([yp1, yp2, ...])]
    """  

    # Polar coordinates (x coordinate = radius,  y coordinate = theta)
    nbrCells = len(mC[0])

    # Define new empty list
    pC = []

    # Populate it with the physical coordinates 
    pC.append(mC[0][:]*np.cos(mC[1][:]))
    pC.append(mC[0][:]*np.sin(mC[1][:]))
    
    return pC


def qinit(state,mx,my):
    """
    Initialize with two Gaussian pulses.
    """

    # The following parameters match the vaules used in clawpack
    # ==========================================================
    # First gaussian pulse
    A1    = 1.    # Amplitude
    beta1 = 40.   # Decay factor
    x1    = -0.5  # x-coordinate of the center
    y1    = 0.    # y-coordinate of the center

    # Second gaussian pulse
    A2    = -1.   # Amplitude
    beta2 = 40.   # Decay factor
    x2    = 0.5   # x-coordinate of the center
    y2    = 0.    # y-coordinate of the center

    
    # Compute location of all grid cell center coordinates and store them
    state.grid.compute_p_center(recompute=True)

    xp = state.grid.p_center[0]
    yp = state.grid.p_center[1]
    state.q[0,:,:] = A1*np.exp(-beta1*(np.square(xp-x1) + np.square(yp-y1)))\
                   + A2*np.exp(-beta2*(np.square(xp-x2) + np.square(yp-y2)))


def setaux(state,mx,my):
    """ 
    Set auxiliary array
    aux[0,i,j] is edge velocity at "left" boundary of grid point (i,j)
    aux[1,i,j] is edge velocity at "bottom" boundary of grid point (i,j)
    aux[2,i,j] = kappa  is ratio of cell area to (dxc * dyc)
    """    
    
    # Compute location of all grid cell corner coordinates and store them
    state.grid.compute_p_edge(recompute=True)

    # Get grid spacing
    dxc = state.grid.d[0]
    dyc = state.grid.d[1]
    pcorners = state.grid.p_edge

    aux = velocities_capa(pcorners[0],pcorners[1],dxc,dyc)
    return aux


def velocities_upper(grid,dim,t,auxbc,mbc):
    """
    Set the velocities for the ghost cells outside the outer radius of the annulus.
    """
    from mapc2p import mapc2p

    mx = grid.ng[0]
    my = grid.ng[1]
    dxc = grid.d[0]
    dyc = grid.d[1]

    if dim == grid.dimensions[0]:
        xc1d = grid.lower[0]+dxc*(np.arange(mx+mbc,mx+2*mbc+1)-mbc)
        yc1d = grid.lower[1]+dyc*(np.arange(my+2*mbc+1)-mbc)
        yc,xc = np.meshgrid(yc1d,xc1d)

        xp,yp = mapc2p(xc,yc)

        auxbc[:,-mbc:,:] = velocities_capa(xp,yp,dxc,dyc)

    else:
        raise Exception('Custum BC for this boundary is not appropriate!')


def velocities_lower(grid,dim,t,auxbc,mbc):
    """
    Set the velocities for the ghost cells outside the inner radius of the annulus.
    """
    from mapc2p import mapc2p

    my = grid.ng[1]
    dxc = grid.d[0]
    dyc = grid.d[1]

    if dim == grid.dimensions[0]:
        xc1d = grid.lower[0]+dxc*(np.arange(mbc+1)-mbc)
        yc1d = grid.lower[1]+dyc*(np.arange(my+2*mbc+1)-mbc)
        yc,xc = np.meshgrid(yc1d,xc1d)

        xp,yp = mapc2p(xc,yc)

        auxbc[:,0:mbc,:] = velocities_capa(xp,yp,dxc,dyc)

    else:
        raise Exception('Custum BC for this boundary is not appropriate!')


def velocities_capa(xp,yp,dx,dy):

    mx = xp.shape[0]-1
    my = xp.shape[1]-1
    aux = np.empty((3,mx,my), order='F')

    # Bottom-left corners
    xp0 = xp[:mx,:my]
    yp0 = yp[:mx,:my]

    # Top-left corners
    xp1 = xp[:mx,1:]
    yp1 = yp[:mx,1:]

    # Top-right corners
    xp2 = xp[1:,1:]
    yp2 = yp[1:,1:]

    # Top-left corners
    xp3 = xp[1:,:my]
    yp3 = yp[1:,:my]

    # Compute velocity component
    aux[0,:mx,:my] = (stream(xp1,yp1)- stream(xp0,yp0))/dy
    aux[1,:mx,:my] = -(stream(xp3,yp3)- stream(xp0,yp0))/dx

    # Compute area of the physical element
    area = 1./2.*( (yp0+yp1)*(xp1-xp0) +
                   (yp1+yp2)*(xp2-xp1) +
                   (yp2+yp3)*(xp3-xp2) +
                   (yp3+yp0)*(xp0-xp3) )
    
    # Compute capa 
    aux[2,:mx,:my] = area/(dx*dy)

    return aux

    
def stream(xp,yp):
    """ 
    Calculates the stream function in physical space.
    Clockwise rotation. One full rotation corresponds to 1 (second).
    """
    streamValue = np.pi*(xp**2 + yp**2)

    return streamValue


def advection_annulus(use_petsc=False,iplot=0,htmlplot=False,outdir='./_output',solver_type='classic'):
    #===========================================================================
    # Import libraries
    #===========================================================================
    if use_petsc:
        import petclaw as pyclaw
    else:
        import pyclaw

    #===========================================================================
    # Setup solver and solver parameters
    #===========================================================================
    if solver_type == 'classic':
        solver = pyclaw.ClawSolver2D()
    elif solver_type == 'sharpclaw':
        solver = pyclaw.SharpClawSolver2D()


    solver.mthbc_lower[0] = pyclaw.BC.outflow
    solver.mthbc_upper[0] = pyclaw.BC.outflow
    solver.mthbc_lower[1] = pyclaw.BC.periodic
    solver.mthbc_upper[1] = pyclaw.BC.periodic

    solver.mthauxbc_lower[0] = pyclaw.BC.custom
    solver.mthauxbc_upper[0] = pyclaw.BC.custom
    solver.user_aux_bc_lower = velocities_lower
    solver.user_aux_bc_upper = velocities_upper
    solver.mthauxbc_lower[1] = pyclaw.BC.periodic
    solver.mthauxbc_upper[1] = pyclaw.BC.periodic

    solver.mwaves = 1

    solver.dim_split = 0
    solver.order_trans = 2
    solver.order = 2

    solver.dt_initial = 0.1
    solver.cfl_max = 0.5
    solver.cfl_desired = 0.2

    solver.limiters = pyclaw.limiters.tvd.vanleer

    #===========================================================================
    # Initialize grid and state, then initialize the solution associated to the 
    # state and finally initialize aux array
    #===========================================================================
    # Grid:
    xlower = 0.2
    xupper = 1.0
    mx = 40

    ylower = 0.0
    yupper = np.pi*2.0
    my = 120

    x = pyclaw.Dimension('x',xlower,xupper,mx)
    y = pyclaw.Dimension('y',ylower,yupper,my)
    grid = pyclaw.Grid([x,y])
    grid.mapc2p = mapc2p_annulus # Override default_mapc2p function implemented in grid.py

    # State:
    meqn = 1  # Number of equations
    state = pyclaw.State(grid,meqn)

    
    # Set initial solution
    # ====================
    qinit(state,mx,my) # This function is defined above

    # Set auxiliary array
    # ===================
    state.aux = setaux(state,mx,my) # This function is defined above
    state.mcapa = 2

    
    #===========================================================================
    # Set up controller and controller parameters
    #===========================================================================
    claw = pyclaw.Controller()
    claw.keep_copy = False
    claw.outstyle = 1
    claw.nout = 25
    claw.tfinal = 1.0
    claw.solution = pyclaw.Solution(state)
    claw.solver = solver
    claw.outdir = outdir

    #===========================================================================
    # Solve the problem
    #===========================================================================
    status = claw.run()

    #===========================================================================
    # Plot results
    #===========================================================================
    if htmlplot:  pyclaw.plot.html_plot(outdir=outdir)
    if iplot:     pyclaw.plot.interactive_plot(outdir=outdir)



if __name__=="__main__":
    from pyclaw.util import run_app_from_main
    output = run_app_from_main(advection_annulus)
    print 'Error: ',output




