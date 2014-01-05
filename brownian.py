# encoding: utf-8  μ αβγδ εζηθ κλμν ξοπρ ςστυ φχψω
"""
PyBroMo - A single molecule diffusion simulator in confocal geometry.

Copyright (C) 2013 Antonino Ingargiola tritemio@gmail.com

This is the main module of PyBroMo. Import (or run) it to perform a simulation.
"""

import os
import cPickle as pickle
from glob import glob
from itertools import izip

import numpy.random as NR
import numpy as np
from numpy import array, arange, sqrt
import matplotlib.pyplot as plt

from path_def import *
from psflib import GaussianPSF, NumericPSF
from scroll_gui import ScrollingToolQT
import loadutils as lu
from storage import Storage

## Avogadro constant
NA = 6.022141e23    # [mol^-1]

def load_simulation(fname):
    store = Storage(fname, overwrite=False)
    params = store.get_sim_parameters()

    psf = NumericPSF()
    box = Box(x1=-4.e-6, x2=4.e-6, y1=-4.e-6, y2=4.e-6, z1=-6e-6, z2=6e-6)
    P = gen_particles(params['np'], box)
    S = ParticlesSimulation(D=params['D'], t_step=params['t_step'],
                            t_max=params['t_max'],
                            particles=P, box=box, psf=psf)
    S.store = store
    S.emission = S.store.data_file.root.trajectories.emission
    S.chunk_size = 2**19
    #self.store_fname = fname+self.compact_name()
    #self.store = Storage(self.store_fname, self.get_params(),
    #                     overwrite=overwrite)
    #kwargs = dict(chunksize=self.chunk_size, comp_filter=comp_filter)
    #self.emission_tot = self.store.add_emission_tot(**kwargs)
    return S

def merge_timestamps(timestamps_list, kind='quicksort'):
    timestamps = np.hstack(timestamps_list)
    particle = np.hstack([np.ones(ts.size, dtype='uint8')
                            for ts in timestamps_list])
    argsort = timestamps.argsort(kind=kind)
    return timestamps[argsort], particle[argsort]

def merge_timestamps(timestamps_list, kind='quicksort'):
    timestamps = np.hstack(timestamps_list)
    particle = np.hstack([np.ones(ts.size, dtype='uint8')
                            for ts in timestamps_list])
    argsort = timestamps_p.argsort(kind=kind)
    return timestamps[argsort], particle[argsort]

class Box:
    """The simulation box"""
    def __init__(self, x1, x2, y1, y2, z1, z2):
        self.x1, self.x2 = x1, x2
        self.y1, self.y2 = y1, y2
        self.z1, self.z2 = z1, z2
        self.b = array([[x1, x2], [y1, y2], [z1, z2]])

    def volume(self):
        """Box volume in m^3."""
        return (self.x2 - self.x1) * (self.y2 - self.y1) * (self.z2 - self.z1)

    def volume_L(self):
        """Box volume in liters."""
        return self.volume()*1e3

    def __repr__(self):
        return u"Box: X %.1fum, Y %.1fum, Z %.1fum" % (
                (self.x2 - self.x1)*1e6,
                (self.y2 - self.y1)*1e6,
                (self.z2 - self.z1)*1e6)


class Particle:
    """Class to describe a single particle"""
    def __init__(self, x0=0, y0=0, z0=0):
        self.x0, self.y0, self.z0 = x0, y0, z0
        self.r0 = array([x0, y0, z0])


def wrap_periodic(a, a1, a2):
    """Folds all the values of `a` outside [a1..a2] inside that intervall.
    This function is used to apply periodic boundary contitions.
    """
    a -= a1
    wrapped = np.mod(a, a2-a1) + a1
    return wrapped

def iter_chunk_size(num_samples, chunk_size):
    """Iterator used to iterate in chunks over an array of size `num_samples`.
    At each iteration returns `chunk_size` except for the last iteration.
    """
    last_chunk_size = np.mod(num_samples, chunk_size)
    for i in xrange(int(num_samples/chunk_size)):
        yield chunk_size
    if last_chunk_size > 0:
        yield last_chunk_size

def iter_chunk_slice(num_samples, chunk_size):
    """Iterator used to iterate in chunks over an array of size `num_samples`.
    At each iteration returns a slice of size `chunk_size` except for the
    last iteration (where the slice is smaller, potentially).
    """
    i = 0
    for c_size in iter_chunk_size(num_samples, chunk_size):
        yield slice(i, i + c_size)
        i += c_size

def reduce_chunk(func, array):
    """Reduce with `func`, chunk by chunk, the passed pytable `array`.
    """
    res = []
    for slice in iter_chunk_slice(array.shape[-1], array.chunkshape[-1]):
        res.append(func(array[..., slice]))
    return func(res)

def map_chunk(func, array, out_array):
    """Map with `func`, chunk by chunk, the input pytable `array`.
    The result is store in the output pytable array `out_array`.
    """
    for slice in iter_chunk_slice(array.shape[-1], array.chunkshape[-1]):
        out_array.append(func(array[..., slice]))
    return out_array


class ParticlesSimulation(object):
    """Class that performs the Brownian motion simulation of N particles.
    """
    def __init__(self, D, t_step, t_max, particles, box, psf, EID=0, ID=0):
        """Initialize the simulation parameters:
        `D`: diffusion coefficient (m/s^2)
        `t_step`: time step (s)
        `particles`: list of `Particle` objects
        `box`: a `Box` object defining the simulation boundaries
        `psf`: a "PSF" object (`GaussianPSF` or `NumericPSF`) defining the PSF
        `EID`: is an ID that identifies the engine on which the simulation
            runs. It's a way to distinguish simulations that may otherwise
            appear identical.
        `ID`: is a number that identify the simulation, for ex. if you run
            the same multiple times on the same engine you can assign different
            ID.
        The EID and ID are shown in the string representation and are used
        to save unique file names.
        """
        self.particles = particles
        self.box = box
        self.psf = psf
        self.np = len(particles)
        self.D = D
        self.t_step = t_step
        self.t_max = t_max
        self.ID = ID
        self.EID = EID
        self.n_samples = int(t_max/t_step)
        self.sigma = sqrt(2*D*3*t_step)

    def __repr__(self):
        s = repr(self.box)
        s += "\nD %.2g, #Particles %d, t_step %.1fus, t_max %.1fs" % (
                self.D, self.np, self.t_step*1e6, self.t_max)
        s += " EID_ID %d %d" % (self.EID, self.ID)
        return s

    def compact_name_core(self):
        """Compact representation of simulation parameters (no EID and t_max)
        """
        Moles = self.concentration()
        return "D%.2g_%dP_%dpM_step%.1fus_ID%d" % (
                self.D, self.np, Moles*1e12, self.t_step*1e6, self.ID)

    def compact_name(self):
        """Compact representation of all simulation parameters
        """
        # this can be made more robust for ID > 9 (double digit)
        s = self.compact_name_core()[:-4]
        s += "_t_max%.1fs_ID%d-%d" % (self.t_max, self.EID, self.ID)
        return s

    def get_params(self):
        """Return a dict containing all the simulation parameters.

        The values are 2-element tuples: first element is the value and
        second element is a string describing the parameter (metadata).
        """
        params = dict(
            D = (self.D, 'Diffusion coefficient (m^2/s)'),
            t_step = (self.t_step, 'Simulation time-step (s)'),
            t_max = (self.t_max, 'Simulation total time (s)'),
            ID = (self.ID, 'Simulation ID (int)'),
            EID = (self.EID, 'IPython Engine ID (int)'),
            np = (self.np, 'Number of simulated particles'),
            pico_mol = (self.concentration()*1e12,
                        'Particles concentration (pM)')
            )
        return params

    def print_RAM(self):
        """Print RAM needed to simulate the current set of parameters."""
        float_size = 8
        size_MB = (self.n_samples*float_size/(1024*1024))
        print "  Number of particles:", self.np
        print "  Number of time steps:", self.n_samples
        print "  Emission array size: %.1f MB (total_emission=True) " % size_MB
        print "  Emission array size: %.1f MB (total_emission=False)" % \
                (size_MB*self.np)
        print "  Position array size: %.1f MB " % (3*size_MB*self.np)

    def concentration(self):
        """Return the concentration (in Moles) of the particles in the box.
        """
        return (self.np/NA)/self.box.volume_L()

    def sim_motion_em(self, delete_pos=True, total_emission=True):
        """Simulate Brownian motion and emission rates in one step.
        This method simulates sequentially one particle a time (uses less RAM).
        `delete_pos` allows to discard the particle trajectories and save only
                the emission.
        `total_emission` choose to save a single emission array for all the
                particles (if True), or save the emission of each single
                particle (if False). In the latter case `.em` will be a 2D
                array (#particles x time). Otherwise `.em` is (1 x time).
        """
        n_samples = self.n_samples
        if total_emission:
            self.em = np.zeros((1, n_samples), dtype=np.float64)
        else:
            self.em = np.zeros((self.np, n_samples), dtype=np.float64)
        POS = []
        pid = os.getpid()
        for i, p in enumerate(self.particles):
            print "[%4d] Simulating particle %d " % (pid, i)
            delta_pos = NR.normal(loc=0, scale=self.sigma, size=3*n_samples)
            delta_pos = delta_pos.reshape(3, n_samples)
            pos = np.cumsum(delta_pos, axis=-1, out=delta_pos)
            pos += p.r0.reshape(3, 1)
            # Coordinates wrapping using periodic boundary conditions
            for coord in (0, 1, 2):
                pos[coord] = wrap_periodic(pos[coord], *self.box.b[coord])

            # Sample the PSF along i-th trajectory then square to account
            # for emission and detection PSF.
            Ro = sqrt(pos[0]**2 + pos[1]**2)  # radial pos. on x-y plane
            Z = pos[2]
            current_em = self.psf.eval_xz(Ro, Z)**2
            if total_emission:
                # Add the current particle emission to the total emission
                self.em += current_em
            else:
                # Store the individual emission of current particle
                self.em[i] = current_em

            if not delete_pos: POS.append(pos.reshape(1, 3, n_samples))
        if not delete_pos: self.pos = np.concatenate(POS)

    def sim_timetrace(self, max_em_rate=1, bg_rate=0):
        """Draw random emitted photons from Poisson(emission rates)."""
        self.bg_rate = bg_rate
        em_rates = (self.em.sum(axis=0)*max_em_rate + bg_rate)*self.t_step
        self.tt = NR.poisson(lam=em_rates).astype(np.uint8)

    def open_store(self, fname='store0_', chunk_size=2**19, overwrite=True,
                   comp_filter=None):
        self.chunk_size = chunk_size
        self.store_fname = fname+self.compact_name()
        self.store = Storage(self.store_fname, self.get_params(),
                             overwrite=overwrite)
        kwargs = dict(chunksize=self.chunk_size, comp_filter=comp_filter)
        self.emission_tot = self.store.add_emission_tot(**kwargs)
        self.emission = self.store.add_emission(**kwargs)

    def sim_motion_em_chunk(self, delete_pos=True, total_emission=True):
        """Simulate Brownian motion and emission rates in one step.
        This method simulates sequentially one particle a time (uses less RAM).
        `delete_pos` allows to discard the particle trajectories and save only
                the emission.
        `total_emission` choose to save a single emission array for all the
                particles (if True), or save the emission of each single
                particle (if False). In the latter case `.em` will be a 2D
                array (#particles x time). Otherwise `.em` is (1 x time).
        """
        if 'store' not in self.__dict__:
            self.open_store()

        for c_size in iter_chunk_size(self.n_samples, self.chunk_size):
            if total_emission:
                em = np.zeros((c_size), dtype=np.float64)
            else:
                em = np.zeros((self.np, c_size), dtype=np.float64)
            POS = []
            pid = os.getpid()
            for i, p in enumerate(self.particles):
                print "[%4d] Simulating particle %d " % (pid, i)
                delta_pos = NR.normal(loc=0, scale=self.sigma, size=3*c_size)
                delta_pos = delta_pos.reshape(3, c_size)
                pos = np.cumsum(delta_pos, axis=-1, out=delta_pos)
                pos += p.r0.reshape(3, 1)
                # Coordinates wrapping using periodic boundary conditions
                for coord in (0, 1, 2):
                    pos[coord] = wrap_periodic(pos[coord], *self.box.b[coord])

                # Sample the PSF along i-th trajectory then square to account
                # for emission and detection PSF.
                Ro = sqrt(pos[0]**2 + pos[1]**2)  # radial pos. on x-y plane
                Z = pos[2]
                current_em = self.psf.eval_xz(Ro, Z)**2
                if total_emission:
                    # Add the current particle emission to the total emission
                    em += current_em
                else:
                    # Store the individual emission of current particle
                    em[i] = current_em
                if not delete_pos: POS.append(pos.reshape(1, 3, n_samples))

            ## Append em to the permanent storage
            # if total_emission is just a linear array
            # otherwise is an hstack of what is saved and em (self.np, c_size)
            em_store = self.emission_tot if total_emission else self.emission
            em_store.append(em)
            if not delete_pos: self.pos = np.concatenate(POS)
        em_store.flush()

    def sim_timetrace_chunkt(self, max_em_rate=1, bg_rate=0, comp_filter=None):
        """Draw random emitted photons from Poisson(emission rates)."""
        self.bg_rate = bg_rate
        self.timetrace_tot = self.store.add_timetrace_tot(
                chunksize=self.chunk_size, comp_filter=comp_filter,
                overwrite=True
                )
        for c_slice in iter_chunk_slice(self.n_samples, self.chunk_size):
            em_tot_chunk = self.emission_tot[c_slice]
            em_rates = (em_tot_chunk*max_em_rate + bg_rate)*self.t_step
            tt = NR.poisson(lam=em_rates).astype(np.uint8)
            self.timetrace_tot.append(tt)
        self.timetrace_tot.flush()

    def sim_timetrace_chunk(self, max_em_rate=1, bg_rate=0, comp_filter=None,
                            chunk_size=2**19):
        """Draw random emitted photons from Poisson(emission rates)."""
        self.bg_rate = bg_rate
        self.timetrace_p = self.store.add_timetrace(
                chunksize=chunk_size, comp_filter=comp_filter,
                overwrite=True
                )
        for c_slice in iter_chunk_slice(self.n_samples, chunk_size):
            em_chunk = self.emission[:, c_slice]
            em_rates = (em_chunk*max_em_rate + bg_rate)*self.t_step
            tt = NR.poisson(lam=em_rates).astype(np.uint8)
            for timetrace_single, tt_single in zip(self.timetrace_p, tt):
                timetrace_single.append(tt_single)
        for tt_i in self.timetrace_p:
            tt_i.flush()

    def gen_ph_times_chunk(self):
        """Generate timestamps from binnned timetraces in `self.timetrace_p`.

        Timestamps (int64) are multiplied by 10 to increase the resolution.
        Multiple counts in the same bin are distributed adding a fraction
        of the bin (i.e. a number between 1 and 9).
        """
        fractions = [5, 2, 8, 4, 9, 1, 7, 3, 6]
        timestamps_p = []
        for timetrace_pi in self.timetrace_p:
            PH = [timetrace_pi.get_where_list('counts >= 1')]
            max_counts = timetrace_pi[PH[0]].astype('u1').max()
            assert max_counts < 10
            PH[0] *= 10
            for frac, v in izip(fractions, range(2, max_counts + 1)):
                PH.append(timetrace_pi.get_where_list('counts >= %d' % v)*10)
                PH[-1] += frac
            timestamps_p.append(np.hstack(PH).astype(np.int64))
        return timestamps_p

    def gen_ph_times_chunkt(self):
        """Generate timestamps of emitted photons from the Poisson events
        extracted by `sim_timetrace()`
        """
        assert self.n_samples < 2**31
        iph = arange(self.np, dtype=np.uint32)

        PH = []
        for v in range(1, map_chunk(np.max, self.timetrace_tot) + 1):
            PH.append(iph[self.tt >= v])
        ph_times = np.hstack(PH).astype(np.float64)

        # Index of 1st time with V photons per bins, for each V >= 2
        I = np.cumsum(array([ph.size for ph in PH]))
        #print I
        fraction = 0.5
        for iph1, iph2 in zip(I[:-1], I[1:]):
            ph_times[iph1:iph2] += fraction
            fraction /= 2.
            #print iph1, iph2
        ph_times.sort()
        ph_times *= self.t_step
        self.ph_times = ph_times


    def gen_ph_times(self):
        """Generate timestamps of emitted photons from the Poisson events
        extracted by `sim_timetrace()`
        """
        iph = arange(self.tt.size, dtype=np.uint32)
        PH = []
        for v in range(1, self.tt.max()+1):
            PH.append(iph[self.tt >= v])
        # Index of 1st time with V photons per bins, for each V >= 2
        I = np.cumsum(array([ph.size for ph in PH]))
        #print I
        ph_times = np.hstack(PH).astype(np.float64)
        fraction = 0.5
        for iph1, iph2 in zip(I[:-1], I[1:]):
            ph_times[iph1:iph2] += fraction
            fraction /= 2.
            #print iph1, iph2
        ph_times.sort()
        ph_times *= self.t_step
        self.ph_times = ph_times

    def time(self, dec=1):
        """Return the time axis with decimation `dec` (memoized)
        """
        if not hasattr(self, "_time"): self._time = dict()
        if not dec in self._time:
            # Add the new time axis to the cache
            self._time[dec] = arange(self.n_samples/dec)*(self.t_step*dec)
        return self._time[dec]

    def dump(self, dir_='.', prefix='bromo_sim'):
        """Save itself in `dir_` in a file named using the simul. parameters.
        """
        fname = dir_+'/'+prefix+'_'+self.compact_name()+'.pickle'
        pickle.dump(self, open(fname, 'wb'), protocol=2)
        print "Saved to", fname

    def load(self, dir_='.', prefix='bromo_sim'):
        """Try to load a simulation named according to current parameters.
        Look in `dir_` for a file named in the same way as the `.dump()` method
        would with the current set of parameters.
        If the file is found is unpickled and returned, otherwise returns None.
        """
        Sim = None
        fname = dir_+'/'+prefix+'_'+self.compact_name()+'.pickle'
        try:
            Sim = pickle.load(open(fname, 'rb'))
            print "Loaded:", fname
        except IOError:
            print "No matching simulation file found."
        return Sim


def load_sim_id(ID, glob_str='*', EID=None, dir_='.', prefix='bromo_sim',
        verbose=False):
    """Try to load a simulation with specified ID.
    """
    # NOTE: if EID is not passed use eid from global scope
    if EID is None: EID = eid
    Sim = None
    try:
        pattern = dir_+'/'+prefix+'%sID%d-%d.pickle' % (glob_str, EID, ID)
        if verbose: print pattern
        fname = glob(pattern)
        if len(fname) > 1: print "ERROR: More than 1 file matched!"
        assert len(fname) == 1
        Sim = pickle.load(open(fname[0], 'rb'))
        print "Loaded:\n", fname[0]
    except:
        print "No matching simulation file found."
    return Sim

##
# Functions to manage/merge multiple simulations
#
def merge_ph_times(ph_times_list, time_block):
    """Build an array of timestamps joining the arrays in `ph_times_list`.
    `time_block` is the duration of each array of timestamps.
    """
    offsets = np.arange(len(ph_times_list))*time_block
    cum_sizes = np.cumsum([ph.size for ph in ph_times_list])
    ph_times = np.zeros(cum_sizes[-1])
    i1 = 0
    for i2, ph, offset in zip(cum_sizes, ph_times_list, offsets):
        ph_times[i1:i2] = ph + offset
        i1 = i2
    return ph_times

def merge_DA_ph_times(ph_times_d, ph_times_a):
    """Returns the merged timestamps of Donor and Acceptor and a bool mask for A
    """
    ph_times = np.hstack([ph_times_d, ph_times_a])
    a_em = np.hstack([np.zeros(ph_times_d.size, dtype=np.bool),
            np.ones(ph_times_a.size, dtype=np.bool)])
    index_sort = ph_times.argsort()
    return ph_times[index_sort], a_em[index_sort]

def merge_particle_emission(SS):
    """Returns a sim object summing the emissions and particles in SS (list).
    """
    # Merge all the particles
    P = reduce(lambda x, y: x+y, [Si.particles for Si in SS])
    s = SS[0]
    S = ParticlesSimulation(D=s.D, t_step=s.t_step, t_max=t_max,
            particles=P, box=s.box, psf=s.psf)
    S.em = np.zeros(s.em.shape, dtype=np.float64)
    for Si in SS:
        S.em += Si.em
    return S

def parallel_gen_timestamps(dview, max_em_rate, bg_rate):
    """Generate timestamps from a set of remote simulations in `dview`.
    Assumes that all the engines have an `S` object already containing
    an emission trace (`S.em`). The "photons" timestamps are generated
    from these emission traces and merged into a single array of timestamps.
    `max_em_rate` and `bg_rate` are passed to `S.sim_timetrace()`.
    """
    dview.execute("S.sim_timetrace(max_em_rate=%f, bg_rate=%f)" % \
            (max_em_rate, bg_rate))
    dview.execute("S.gen_ph_times()")
    PH = dview['S.ph_times']
    # Assuming all t_max equal, just take the first
    t_max = dview['S.t_max'][0]
    t_tot = np.sum(dview['S.t_max'])
    dview.execute("sim_name = S.compact_name_core()")
    # Core names contains no ID or t_max
    sim_name = dview['sim_name'][0]
    ph_times = merge_ph_times(PH, time_block=t_max)
    return ph_times, t_tot, sim_name

##
# Plot simulation functions
#

def plot_tracks(S):
    fig, AX = plt.subplots(2, 1, figsize=(6, 9), sharex=True)
    plt.subplots_adjust(left=0.12, right=0.95, top=0.95, bottom=0.05,
            hspace=0.05)
    plt.suptitle("%.1f ms diffusion" % (S.t_step*S.n_samples*1e3))

    for ip in range(S.np):
        x, y, z = S.pos[ip]
        x0, y0, z0 = S.particles[ip].r0
        plot_kwargs = dict(ls='', marker='o', mew=0, ms=1, alpha=0.2)
        l, = AX[1].plot(x*1e6, y*1e6, **plot_kwargs)
        AX[1].plot([x0*1e6], [y0*1e6], 'o', color=l.get_color())
        AX[0].plot(x*1e6, z*1e6, color=l.get_color(), **plot_kwargs)
        AX[0].plot([x0*1e6], [z0*1e6], 'o', color=l.get_color())

    AX[1].set_ylabel("y (um)")
    AX[1].set_xlabel("x (um)")
    AX[0].set_ylabel("z (um)")
    AX[0].grid(True); AX[1].grid(True)

    if S.psf.name == 'gauss':
        sig = S.psf.s
    else:
        sig = array([0.1, 0.1, 0.3])*1e-6
    ## Draw an outline of the PSF
    a = arange(360)/360.*2*np.pi
    rx, ry, rz = (sig)  # draw radius at 3 sigma
    AX[1].plot((rx*np.cos(a))*1e6, (ry*np.sin(a))*1e6, lw=2, color='k')
    AX[0].plot((rx*np.cos(a))*1e6, (rz*np.sin(a))*1e6, lw=2, color='k')

def plot_emission(S, dec=1, scroll_gui=False, multi=False, ms=False):
    fig = plt.figure()
    plt.title("%d Particles, %.1f s diffusion, %d pM" % (S.np,
            S.t_step*S.n_samples, S.concentration()*1e12))
    plt.xlabel("Time (s)"); plt.ylabel("Emission rate [A.U.]"); plt.grid(1)
    if ms: plt.xlabel("Time (ms)")
    if multi:
        for em in S.em:
            time = S.time(dec=dec) if not ms else S.time(dec=dec)*1e3
            plt.plot(time, em[::dec], alpha=0.5)
    else:
        time = S.time(dec=dec) if not ms else S.time(dec=dec)*1e3
        plt.plot(time, S.em.sum(axis=0)[::dec], alpha=0.5)
    s = None
    if scroll_gui: s = ScrollingToolQT(fig)
    return s

def plot_timetrace(S, rebin=2e3, scroll_gui=False):
    fig = plt.figure()
    plt.title("%d Particles, %.1f s diffusion, %d pM, bin=%.1fms" % (S.np,
            S.t_step*S.n_samples, S.concentration()*1e12, S.t_step*rebin*1e3))
    plt.xlabel("Time (s)"); plt.ylabel("Emission rate [A.U.]"); plt.grid(1)
    trace = S.tt.reshape(-1, rebin).sum(axis=1)
    t_trace = (arange(trace.size)+1)*(S.t_step*rebin)
    plt.plot(S.time(), S.em.sum(axis=0)*100, alpha=0.4)
    plt.plot(t_trace, trace, color='k', alpha=0.7, drawstyle='steps')
    if scroll_gui: return ScrollingToolQT(fig)


def gen_particles(N, box):
    """Generate `N` Particle() objects with random position in `box`.
    """
    X0 = NR.rand(N)*(box.x2-box.x1) + box.x1
    Y0 = NR.rand(N)*(box.y2-box.y1) + box.y1
    Z0 = NR.rand(N)*(box.z2-box.z1) + box.z1
    return [Particle(x0=x0, y0=y0, z0=z0) for x0, y0, z0 in zip(X0, Y0, Z0)]


if __name__ == '__main__':
    # Simulation time step
    t_step = 0.5e-6     # seconds

    # Diffusion coefficient
    Du = 12.0           # um^2 / s
    D = Du*(1e-6)**2

    # Time duration of the simulation
    t_max = 0.3        # seconds
    n_samples = int(t_max/t_step)

    # PSF definition
    #ss = 0.2*1e-6      # lateral dimension (sigma)
    #psf = GaussianPSF(xc=0, yc=0, zc=0, sx=ss, sy=ss, sz=3*ss)
    psf = NumericPSF()

    # Box definition
    box = Box(x1=-4.e-6, x2=4.e-6, y1=-4.e-6, y2=4.e-6, z1=-6e-6, z2=6e-6)

    # Particles definition
    #p1 = Particle(x0=-3e-6)
    #p2 = Particle(x0=3e-6)
    #p3 = Particle(y0=-3e-6)
    #p4 = Particle(y0=3e-6)
    #P = [p1,p2,p3,p4]
    P = gen_particles(15, box)

    # Brownian motion and emission simulation
    S = ParticlesSimulation(D=D, t_step=t_step, t_max=t_max,
                            particles=P, box=box, psf=psf)
    #S.sim_motion_em(delete_pos=False)
    #S.sim_timetrace(max_em_rate=3e5, bg_rate=10e3)
    #S.gen_ph_times()

    #plot_tracks(S)
    #plot_emission(S)

