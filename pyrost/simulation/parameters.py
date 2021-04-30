"""
Examples
--------

Generate parameters, which could be later parsed to :class:`pyrost.simulation.STSim`
in order to perform the simulation.

>>> import pyrost.simulation as st_sim
>>> st_params = st_sim.parameters()
>>> print(st_params)
{'defocus': 400.0, 'det_dist': 2000000.0, 'step_size': 0.1, 'n_frames': 300,
'fs_size': 2000, 'ss_size': 1000, 'pix_size': 55.0, '...': '...'}
"""
import os
import numpy as np
from ..protocol import INIParser, ROOT_PATH
from ..bin import bar_positions, barcode_profile
from .materials import Material, MLL

PARAMETERS_FILE = os.path.join(ROOT_PATH, 'config/parameters.ini')

class STParams(INIParser):
    """Container with the experimental parameters of
    one-dimensional Speckle Tracking scan. All the experimental
    parameters are enlisted in `attr_dict`.

    Parameters
    ----------
    **kwargs : dict
        Values for the exerimental parameters specified
        in `attr_dict`.

    Attributes
    ----------
    attr_dict : dict
        Dictionary which contains all the experimental
        parameters.
    fmt_dict: dict
        Dictionary which specifies the data types of the
        parameters in `attr_dict`.

    See Also
    --------
    st_sim_param : Full list of experimental parameters.
    """
    attr_dict = {'exp_geom': ('defocus', 'det_dist', 'n_frames',
                              'step_size', 'step_rnd'),
                 'detector': ('fs_size', 'pix_size', 'ss_size'),
                 'source':   ('p0', 'th_s', 'wl'),
                 'lens':     ('alpha', 'ap_x', 'ap_y', 'focus', 'ab_cnt'),
                 'barcode':  ('bar_atn', 'bar_rnd', 'bar_sigma', 'bar_size',
                              'bulk_atn', 'offset'),
                 'system':   ('seed',)}

    fmt_dict = {'exp_geom': 'float', 'exp_geom/n_frames': 'int',
                'detector': 'int', 'detector/pix_size': 'float',
                'source': 'float', 'lens': 'float', 'barcode': 'float',
                'system/seed': 'int'}
    FMT_LEN = 7

    @classmethod
    def lookup_dict(cls):
        """Look-up table between the sections and the parameters.

        Returns
        -------
        dict
            Look-up dictionary.
        """
        lookup = {}
        for section in cls.attr_dict:
            for option in cls.attr_dict[section]:
                lookup[option] = section
        return lookup

    def __init__(self, **kwargs):
        super(STParams, self).__init__(**kwargs)
        self.__dict__['_lookup'] = self.lookup_dict()

    def __iter__(self):
        return self._lookup.__iter__()

    def __contains__(self, attr):
        return attr in self._lookup

    def __getattr__(self, attr):
        if attr in self._lookup:
            return self.__dict__[self._lookup[attr]][attr]
        else:
            raise AttributeError(attr + " doesn't exist")

    def __setattr__(self, attr, value):
        if attr in self._lookup:
            fmt = self.get_format(self._lookup[attr], attr)
            self.__dict__[self._lookup[attr]][attr] = fmt(value)
        else:
            raise AttributeError(attr + ' not allowed')

    def __repr__(self):
        return self._format(self.export_dict()).__repr__()

    def __str__(self):
        return self._format(self.export_dict()).__str__()

    def get_seed(self):
        if self.seed > 0:
            return self.seed
        else:
            return np.random.default_rng().integers(0, np.iinfo(np.int_).max,
                                                    endpoint=False)

    @classmethod
    def import_dict(cls, **kwargs):
        """Initialize experimental parameters from a dictionary `kwargs`.

        Parameters
        ----------
        **kwargs : dict
            Dictionary with experimental parameters.

        Returns
        -------
        STParams
            An :class:`STParams` object with the parameters from `kwargs`.
        """
        init_dict = {}
        for section in cls.attr_dict:
            init_dict[section] = {}
            for option in cls.attr_dict[section]:
                init_dict[section][option] = kwargs[option]
        return cls(**init_dict)

    def x_wavefront_size(self):
        r"""Return wavefront array size along the x axis, that
        satisfies the sampling condition.

        Returns
        -------
        n_x : int
            Array size.

        Notes
        -----
        The sampling condition when we propagate the wavefield from
        the lens plane to the sample plane is as follows:

        .. math::
            N_x >= \frac{\mathrm{max} \left( \Delta x_{lens}, \Delta x_{sample} \right)
            (\Delta x_{lens} + \Delta x_{sample})}{\lambda d} =
            \frac{4 a_x^2 \mathrm{max} \left( f, df \right)}{f^2 \lambda}

        Whereupon, the sampling condition when we propagate the wavefield to the detector
        plane is:

        .. math::
            N_x >= \frac{\Delta x_{sample} \Delta x_{det}}{\lambda d} =
            \frac{2 a_x n_{fs} \Delta_{pix} df}{f \lambda d_{det}}
        """
        nx_ltos = int(4 * self.ap_x**2 * max(self.focus, np.abs(self.defocus)) / self.focus**2 / self.wl)
        nx_stod = int(2 * self.fs_size * self.pix_size * self.ap_x * np.abs(self.defocus) / self.focus / self.wl / self.det_dist)
        return max(nx_ltos, nx_stod)

    def y_wavefront_size(self):
        r"""Return wavefront array size along the y axis, that
        satisfies the sampling condition.

        Returns
        -------
        n_y : int
            Array size.

        Notes
        -----
        The sampling condition when we propagate the wavefield from
        the lens plane to the sample plane is as follows:

        .. math::
            N_y >= \frac{\mathrm{max} \left( \Delta y_{lens}, \Delta y_{sample} \right)
            (\Delta y_{lens} + \Delta y_{sample})}{\lambda d} =
            \frac{8 a_y^2}{(f + df) \lambda}

        Whereupon, the sampling condition when we propagate the wavefield to the detector
        plane is:

        .. math::
            N_y >= \frac{\Delta y_{sample} \Delta y_{det}}{\lambda d} =
            \frac{2 a_y n_{ss} \Delta_{pix}}{\lambda d_{det}}
        """
        ny_ltos = int(8 * self.ap_y**2 / (self.focus + self.defocus) / self.wl)
        ny_stod = int(2 * self.ss_size * self.pix_size * self.ap_y / self.wl / self.det_dist)
        return max(ny_ltos, ny_stod)

    def lens_wavefronts(self, n_x=None, n_y=None, return_dxdy=False):
        r"""Return wavefields at the lens plane along x and y axes.

        Parameters
        ----------
        n_x : int, optional
            Array size along the x axis. Equals to
            :func:`STParams.x_wavefront_size` if it's None.
        n_y : int, optional
            Array size along the y axis. Equals to
            :func:`STParams.y_wavefront_size` if it's None.
        return_dxdy: bool, optional
            Return step sizes along x and y axes if it's True.

        Returns
        -------
        u0_x : numpy.ndarray
            Wavefront along the x axis.
        u0_y : numpy.ndarray
            Wavefront along the y axis.
        dx : float
            Step size along the x axis [um]. Only if
            `return_dxdy` is True.
        dy : float
            Step size along the y axis [um]. Only if
            `return_dxdy` is True.

        Notes
        -----
        The exit-surface at the lens plane:

        .. math::
            U_0(x) = \Pi(a_x x) \exp
            \left[ -\frac{j \pi x^2}{\lambda f} + j \alpha
            \left( \frac{x - x_{ab_cnt}}{f} \right)^3 \right]

        .. math::
            U_0(y) = \Pi(a_y y)
        """
        if n_x is None:
            n_x = self.x_wavefront_size()
        if n_y is None:
            n_y = self.y_wavefront_size()
        dx, dy = 2 * self.ap_x / n_x, 2 * self.ap_y / n_y
        x0 = dx * np.arange(-n_x // 2, n_x // 2)
        y0 = dy * np.arange(-n_y // 2, n_y // 2)
        x_cnt = (self.ab_cnt - 0.5) * self.ap_x
        u0_x = np.exp(1j * np.pi * x0**2 / self.wl / self.focus - \
                      1j * 1e9 * self.alpha * ((x0 - x_cnt) / self.focus)**3)
        u0_y = np.ones(n_y, dtype=np.complex128)
        u0_x[np.abs(x0) > self.ap_x / 2] = 0
        u0_y[np.abs(y0) > self.ap_y / 2] = 0
        if return_dxdy:
            return u0_x, u0_y, dx, dy
        else:
            return u0_x, u0_y

    def beam_span(self, dist):
        """Return beam span along the x axis at distance `dist`
        from the focal plane.

        Parameters
        ----------
        dist : float
            Distance from the focal plane [um].

        Returns
        -------
        th_lb : float
            Beam's lower bound [um].
        th_ub : float
            Beam's upper bound [um].
        """
        th_lb = -0.5 * self.ap_x / self.focus + self.wl / np.pi * self.alpha * \
                3.75e8 * (self.ap_x / self.focus)**2 / dist
        th_ub = 0.5 * self.ap_x / self.focus + self.wl / np.pi * self.alpha * \
                3.75e8 * (self.ap_x / self.focus)**2 / dist
        return np.tan(th_lb) * dist, np.tan(th_ub) * dist

    def bar_positions(self, dist, rnd_dev=True):
        """Generate a coordinate array of barcode's bar positions at
        distance `dist` from focal plane.

        Parameters
        ----------
        dist : float
            Distance from the focal plane [um].

        Returns
        -------
        bar_pos : numpy.ndarray
            Array of barcode's bar coordinates.

        See Also
        --------
        bin.bar_positions : Full details of randomized barcode steps
            generation algorithm.
        """
        x0, x1 = self.beam_span(dist)
        seed = self.get_seed() if rnd_dev else -1
        return bar_positions(x0=x0 + self.offset, b_dx=self.bar_size, rd=self.bar_rnd,
                             x1=x1 + self.step_size * self.n_frames - self.offset,
                             seed=seed)

    def sample_positions(self):
        """Generate an array of sample's translations with random deviation.

        Returns
        -------
        smp_pos : numpy.ndarray
            Array of sample translations [um].
        """
        rng = np.random.default_rng(self.get_seed())
        rnd_arr = 2 * self.step_rnd * (rng.random(self.n_frames) - 0.5)
        return self.step_size * (np.arange(self.n_frames) + rnd_arr)

    def barcode_profile(self, x_arr, bars, num_threads=1):
        """Generate a barcode's transmission profile at `x_arr`
        coordinates.

        Parameters
        ----------
        bar_pos : numpy.ndarray
            Array of barcode's bar positions [um].
        x_arr : numpy.ndarray
            Array of the coordinates, where the transmission
            coefficients are calculated [um].

        Returns
        -------
        b_tr : numpy.ndarray
            Barcode's transmission profile.

        See Also
        --------
        bin.barcode_profile : Full details of barcode's transmission
            profile generation algorithm.
        """
        return barcode_profile(x_arr=x_arr, bars=bars, bulk_atn=self.bulk_atn,
                               bar_atn=self.bar_atn, bar_sigma=self.bar_sigma,
                               num_threads=num_threads)

    def source_curve(self, dist, dx):
        """Return source's rocking curve profile at `dist` distance from
        the lens.

        Parameters
        ----------
        dist : float
            Distance from the lens to the rocking curve profile [um].
        dx : float
            Sampling distance [um].

        Returns
        -------
        numpy.ndarray
            Source's rocking curve profile.
        """
        sc_sgm, n_sc = self.th_s * dist, np.ceil(8 * self.th_s * dist / dx)
        sc_x = dx * np.arange(-n_sc // 2, n_sc // 2 + 1)
        sc = np.exp(-sc_x**2 / 2 / sc_sgm**2)
        return sc / sc.sum()

    def export_dict(self):
        """Export experimental parameters to :class:`dict`.

        Returns
        -------
        param_dict : dict
            Experimental parameters.
        """
        param_dict = {}
        for section in self.attr_dict:
            for option in self.attr_dict[section]:
                param_dict[option] = self.__dict__[section][option]
        return param_dict

def parameters(**kwargs):
    """Return the default :class:`STParams` object. Override any
    experimental parameters with `**kwargs`.

    Parameters
    ----------
    **kwargs : dict
        Dictionary which contains experimental
        parameters values.

    Returns
    -------
    st_params : STParams
        Default experimental parameters.

    See Also
    --------
    STParams : Full list of the experimental parameters.
    """
    st_params = STParams.import_ini(PARAMETERS_FILE).export_dict()
    st_params.update(**kwargs)
    return STParams.import_dict(**st_params)

class MSParams(INIParser):
    attr_dict = {'multislice':   ('x_step', 'z_step', 'distance'),
                 'mll_mat1':   ('formula', 'density'),
                 'mll_mat2':   ('formula', 'density'),
                 'mll':          ('ap_x', 'n_min', 'n_max', 'focus', 'sigma', 'wavelength')}

    fmt_dict = {'exp_geom': 'float', 'mll_mat1/formula': 'str', 'mll_mat1/density': 'float',
                'mll_mat2/formula': 'str', 'mll_mat2/density': 'float', 'mll/n_min': 'int',
                'mll/n_max': 'int', 'mll/focus': 'float', 'mll/sigma': 'float', 'mll/wavelength': 'float'}

    def __init__(self, **kwargs):
        super(MSParams, self).__init__(**kwargs)
        self.__dict__['_lookup'] = self.lookup_dict()

    @classmethod
    def lookup_dict(cls):
        """Look-up table between the sections and the parameters.

        Returns
        -------
        dict
            Look-up dictionary.
        """
        lookup = {}
        for section in ('exp_geom', 'mll'):
            for option in cls.attr_dict[section]:
                lookup[option] = section
        return lookup

    def __getattr__(self, attr):
        if attr in self._lookup:
            return self.__dict__[self._lookup[attr]][attr]
        else:
            raise AttributeError(attr + " doesn't exist")

    def __setattr__(self, attr, value):
        if attr in self._lookup:
            self.__dict__[self._lookup[attr]][attr] = value
        else:
            raise AttributeError(attr + ' not allowed')

    def get_coords(self):
        mll = self.get_mll()
        x_min, x_max = mll.get_span()
        x_arr = np.arange((x_min - (x_max - x_min) / 2) // self.x_step,
                          (x_max + (x_max - x_min) / 2) // self.x_step)
        return self.x_step * x_arr

    def get_kernel(self, size=None):
        if size is None:
            size = int(10 * self.z_step / self.x_step)
        x_arr = self.x_step * np.arange(-size // 2, size // 2)
        dist = np.sqrt(x_arr**2 + self.z_step**2)
        return self.x_step * self.z_step * np.exp(-2j * np.pi / self.wavelength * dist) / \
               (1j * self.wavelength**0.5 * dist**1.5)

    def get_mat1(self):
        return Material(**self.mll_mat1)

    def get_mat2(self):
        return Material(**self.mll_mat2)

    def get_mll(self):
        layers = np.arange(self.n_min, self.n_max, dtype=int)
        return MLL(mat1=self.get_mat1(), mat2=self.get_mat2(), layers=layers,
                   focus=self.focus, sigma=self.sigma, wavelength=self.wavelength)

    def get_wavefront(self, x_arr):
        return np.where(np.abs(x_arr - x_arr.mean()) < self.ap_x / 2, 1. + 0.j, 0. + 0.j)