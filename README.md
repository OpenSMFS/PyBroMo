Overview
=======

**[PyBroMo](http://tritemio.github.io/PyBroMo/)** is an open-source simulator 
for Brownian-motion diffusion and photon emission of fluorescent particles 
excited by a diffraction limited laser spot.
PyBroMo allows to simulate timestamps of photons emitted during 
[smFRET](http://en.wikipedia.org/wiki/Single-molecule_FRET) experiments, 
including sample background and detectors dark counts.

> For a smFRET burst analysis software see [FRETBursts](https://github.com/tritemio/FRETBursts).

PyBromo simulates 3-D Brownian motion trajectories and emission of an arbitrary number of particles freely diffusing in a simulation volume (a box). 
Inside the simulation box a laser excitation volume (the 
[PSF](http://en.wikipedia.org/wiki/Point_spread_function) of the objective lens)
is defined numerically or analytically (Gaussian shape).  Molecules diffusing 
through the excitation volume emit photons at a rate proportional to the 
local excitation intensity.

A precomputed numerical [PSF](http://en.wikipedia.org/wiki/Point_spread_function)
is included and used by default.
The included numerical PSF is computed through
[rigorous vectorial electromagnetic computations]
(http://dx.doi.org/10.1364/JOSAA.27.000295) using the
[PSFLab](http://onemolecule.chem.uwm.edu/software) software. 
The user can provide a different numerical PSF or,
alternatively, use an analytical Gaussian-shaped PSF.

An overview of the architecture of the simulator can be found 
[below](#architecture).

The user documentation is provided in a series of [IPython Notebook](http://ipython.org/notebook.html) 
(see **[Usage examples](#usage-examples)**). 

Bug fixes and/or enhancements are welcome, just send a [pull request (PR)](https://help.github.com/articles/using-pull-requests).

For more info contact me at tritemio@gmail.com.

Environment
==========

PyBroMo is written in the [python programming language](http://www.python.org/) using the standard 
scientific stack of libraries (numpy, scipy, matplotlib).

Usage examples are given as 
IPython notebooks. 
[IPython Notebook](http://ipython.org/notebook.html) is an interactive web-based environment that allows to mix rich text, math and graphics with (live) code, similarly to the Mathematica environment. 
You can find a static HTML version of the notebooks below in section **[Usage examples](#usage-examples)**. 

Moreover the [IPython environment](http://ipython.org/) allows to easily setup a cluster for parallel computing. Therefore simulation time can be
greatly reduced using a single multi-core PC, multiple PC or a cloud-computing service. Examples on how to perform parallel simulation are provided in the notebooks.

For a tutorial on python in science:

* [Python Scientific Lecture Notes](http://scipy-lectures.github.io/)

You may also want to check these links to the IPython documentation:

* [The IPython Notebook](http://ipython.org/ipython-doc/stable/interactive/notebook.html)
* [Using IPython for parallel computing](http://ipython.org/ipython-doc/stable/parallel/index.html)


#Installation

##MS Windows

In order to run the code you need to install a scientific python
distribution like [Anaconda](https://store.continuum.io/cshop/anaconda/).
The free version of Anaconda includes all the needed dependencies.
Any other scientific python distribution (for example 
[Enthought Canopy](https://www.enthought.com/products/canopy/)) 
will work as well.
 
Once a python distribution is installed, download the latest version
of [PyBroMo](https://github.com/tritemio/PyBroMo) from *GitHub*. 
It's suggested to start using the simulator
launching an IPython Notebook server in the PyBroMo notebook folder
(see the following paragraph) and playing with the examples.

###Configuring IPython Notebook

You need to configure the IPython Notebook launcher to start in the PyBroMo notebook folder. If you put PyBroMo in `C:\PyBroMo` then the notebooks folder will be `C:\PyBroMo\notebooks`.

Just right click on the *IPython Notebook icon* -> *Properties* and paste 
the notebook folder in *Start in*. Apply and close.

Now, double click on the icon and a browser should pop up showing the list
of notebooks. Chrome browser is suggested (to set Chrome as the default browser
in IPython see [this StackOverflow answer](http://stackoverflow.com/questions/15632663/launch-ipython-notebook-with-selected-browser)).


##Linux and Mac OS X

On Linux or Mac OS X you can also use the [Anaconda](https://store.continuum.io/cshop/anaconda/) distribution.

Alternatively you can install the following requirements (hint: on Mac OS X you can use MacPorts):

 - python 2.7.x
 - IPython 1.x
 - matplotlib 1.3.x or greater
 - numpy/scipy (any recent version)
 - modern browser (Chrome suggested)

#Architecture
The simulation domain is defined as 3-D box, centered around the origin. The dimension on each direction (x, y, z) can be different. Periodic boundary conditions are applied.

A particle is described by its initial position. A list of particles with random initial position is generated by an utility function before running the simulation.

The excitation PSF is a function of the position and is centered with maximum on the origin. A realistic PSF obtained by vectorial electromagnetic simulation is precomputed using [PSFLab](http://onemolecule.chem.uwm.edu/software). The PSF is computed for a single wavelength and includes effects such as refractive index mismatch and mismatch between the objective lens correction and the cover-glass thickness. The user can  generate a different PSF using [PSFLab](http://onemolecule.chem.uwm.edu/software). The PSF is generated using circular polarized light so it has cylindrical symmetry and can precomputed only on the x-z plane.
Alternatively, a simple Gaussian PSF can also be used.

The Brownian motion parameters are: the diffusion coefficient, the simulation box, the list of particles, the simulation time step and the simulation final time. 

The Brownian  motion simulation uses constant timesteps (typically 0.5 μs). 
This allows a straightforward and efficient implementation. 
In fact, the trajectory is computed
in a single operation, integrating the (random) array of displacements with the
[`cumsum`](http://docs.scipy.org/doc/numpy/reference/generated/numpy.cumsum.html) command. The drawback of this approach is the high RAM usage, although the
problem can be mitigated (see below).

The instantaneous emission rate of the particle is computed during the Brownian motion simulation, evaluating the PSF intensity at each position. Once the emission rate is computed at all the timesteps, photons are generated stochastically from a [Poisson process](http://en.wikipedia.org/wiki/Poisson_process). The rate of the Poisson process is the sum of the instantaneous emission rate and the background rate. The time bin in which a photon is extracted 
is used as the photon (or dark count) timestamp. 
Photo-physics effects, such as blinking and bleaching, are not currently 
modeled.
However these effect can be easily included simply "modulating" the emission 
rates before generating the photons.

To overcome the problem of high RAM usage of long simulations, the user can choose to delete the particle trajectory after the emission trace has been computed. Moreover, is possible to save a single cumulative array of emissions (for all the particles) instead of having a separate emission trace for each particle. Finally, the computation can be distributed on the nodes of a cluster (IPython cluster). Several batches of simulation can be executed on each node, making possible to simulate an arbitrary long experiment on limited hardware. Thanks to the IPython infrastructure the simulation can be seamless run on a single machine, on a cluster of machines or on a cloud computing server.

#Usage examples

The following links will open (a static version of) the notebooks provided
with PyBroMo. This collection serves both as usage examples and user guide.
If you install the software (see [**Installation**](#installation) section) these notebooks can be
executed.

* [1.1 Run simulation - Single host](http://nbviewer.ipython.org/urls/raw.github.com/tritemio/PyBroMo/master/notebooks/PyBroMo%2520-%25201.1%2520Run%2520simulation%2520-%2520Single%2520host.ipynb)
* [1.2 Run simulation - Parallel](http://nbviewer.ipython.org/urls/raw.github.com/tritemio/PyBroMo/master/notebooks/PyBroMo%2520-%25201.2%2520Run%2520simulation%2520-%2520Parallel.ipynb)
* [2. Generate timestamps - Parallel](http://nbviewer.ipython.org/urls/raw.github.com/tritemio/PyBroMo/master/notebooks/PyBroMo%2520-%25202.%2520Generate%2520timestamps%2520-%2520Parallel.ipynb)
* [3. Generate and export smFRET data](http://nbviewer.ipython.org/urls/raw.github.com/tritemio/PyBroMo/master/notebooks/PyBroMo%2520-%25203.%2520Generate%2520and%2520export%2520smFRET%2520data.ipynb)

You may be also interested in a few notebooks on the theory of Brownian motion
simulation (they don't require PyBroMo):

* [Theory - Introduction to Brownian Motion simulation](http://nbviewer.ipython.org/urls/raw.github.com/tritemio/PyBroMo/master/notebooks/Theory%2520-%2520Introduction%2520to%2520Brownian%2520Motion%2520simulation.ipynb)
* [Theory - On Browniam motion and Diffusion coefficient](http://nbviewer.ipython.org/urls/raw.github.com/tritemio/PyBroMo/master/notebooks/Theory%2520-%2520On%2520Browniam%2520motion%2520and%2520Diffusion%2520coefficient.ipynb)

#Acknowledgements

I wish to thank Xavier Michalet for useful discussions and insight.

This work was supported by NIH grants R01 GM069709 and R01 GM095904.

#License and Copyrights

PyBroMo - A single molecule diffusion simulator in confocal geometry.

Copyright (C) 2013  Antonino Ingargiola - <tritemio@gmail.com>

    This program is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    version 2, as published by the Free Software Foundation.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You can find a full copy of the license in the file LICENSE.txt


[![githalytics.com alpha](https://cruel-carlota.pagodabox.com/7af364b00f555df7cf02932a38b05ddc "githalytics.com")](http://githalytics.com/tritemio/PyBroMo)
