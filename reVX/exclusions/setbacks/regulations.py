# -*- coding: utf-8 -*-
"""
Compute setbacks exclusions
"""
from warnings import warn
import logging

from reVX.exclusions.regulations import AbstractBaseRegulations


logger = logging.getLogger(__name__)


class SetbackRegulations(AbstractBaseRegulations):
    """Setback regulation values. """

    def __init__(self, system_height, regulations_fpath=None,
                 multiplier=None, generic_setback_dist=None):
        """

        Parameters
        ----------
        system_height : float | int
            System height (m) used to resolve local ordinance
            multipliers such as ``"Structure Height Multiplier"``.
        regulations_fpath : str | None, optional
            Path to regulations ``.csv`` or ``.gpkg`` file. At a
            minimum, this file must contain the following columns:

                - ``Feature Type``: Contains labels for the type of
                  setback that each row represents. This should be a
                  `"feature_type"` label that can be found in the
                  :attr:`~reVX.exclusions.setbacks.setbacks.SETBACK_SPECS`
                  dictionary (e.g. ``"structures"``, ``"roads"``,
                  ``"water"``, etc.), unless you have created your own
                  setback calculator using
                  :func:`~reVX.exclusions.setbacks.setbacks.setbacks_calculator`,
                  in which case this label can match the `feature_type`
                  input you used for that function call.
                - ``Feature Subtype``: Contains labels for feature
                  subtypes. The feature subtypes are only used for
                  down-selecting the local regulations that should be
                  applied for a particular feature, so often you can
                  leave this blank or set it to ``None``. If you do
                  specify this value, it should be a
                  `"feature_subtypes_to_exclude"` label that can be
                  found in the
                  :attr:`~reVX.exclusions.setbacks.setbacks.SETBACK_SPECS`
                  dictionary, unless you have created your own setback
                  calculator using
                  :func:`~reVX.exclusions.setbacks.setbacks.setbacks_calculator`,
                  in which case this label can match the
                  `feature_subtypes_to_exclude` input you used for that
                  function call.
                - ``Value Type``: Specifies wether the value is a
                  multiplier or static height. See below for more info.
                - ``Value``: Numeric value of the setback or multiplier.
                - ``FIPS``: Specifies a unique 5-digit code for each
                  county (this can be an integer - no leading zeros
                  required). This is used to match the county
                  regulations to the county's spatial extent.

                  .. NOTE:: This column is optional if the regulations
                     file already includes a ``geometry`` column that
                     defines the spatial boundaries for each row.

            Valid options for the ``Value Type`` are (case-insensitive;
            dashes, underscores, and spaces are interchangeable):

                - "Structure Height Multiplier"
                - "Meters"

            If this input is ``None``, a generic setback of
            ``generic_setback_dist * multiplier`` is used.
            By default ``None``.
        multiplier : int | float | str | None, optional
            A setback multiplier to use if regulations are not supplied.
            This multiplier will be applied to the
            ``generic_setback_dist`` to calculate the setback. If
            supplied along with ``regulations_fpath``, this input will
            be used to apply a setback to all counties not listed in the
            regulations file. By default ``None``.
        generic_setback_dist : float | int | None, optional
            Optional generic setback distance. By default, ``None``.
        """
        self._multi = multiplier
        self._system_height = system_height
        super().__init__(generic_regulation_value=generic_setback_dist,
                         regulations_fpath=regulations_fpath)

    def _preflight_check(self, regulations_fpath):
        """Apply preflight checks to the regulations path and multiplier.

        Run preflight checks on setback inputs:
        1) Ensure either a regulations .csv or
           a setback multiplier (or both) is provided
        2) Ensure regulations has county FIPS, map regulations to county
           geometries from exclusions .h5 file

        Parameters
        ----------
        regulations_fpath : str | None
            Path to regulations .csv file, if `None`, create global
            setbacks.
        """
        super()._preflight_check(regulations_fpath)

        if self._multi is not None:
            logger.debug('Computing setbacks using generic setback distance '
                         'multiplier of {}'.format(self._multi))

        if not regulations_fpath and self._multi is None:
            msg = ('Computing setbacks requires a regulations '
                   '.csv file and/or a generic multiplier!')
            logger.error(msg)
            raise RuntimeError(msg)

    @property
    def multiplier(self):
        """int | float: Generic setback multiplier. """
        return self._multi

    @property
    def system_height(self):
        """float: System height value used for local ordinances."""
        return self._system_height

    @property
    def generic(self):
        """float | None: Regulation value used for global regulations. """
        if self.multiplier is None or self._generic_regulation_value is None:
            return None

        return self._generic_regulation_value * self.multiplier

    def _county_regulation_value(self, county_regulations):
        """Retrieve county regulation setback. """
        setback_type = county_regulations["Value Type"]
        setback = float(county_regulations["Value"])

        if setback_type == "structure height multiplier":
            return setback * self.system_height

        if setback_type != "meters":
            msg = ("Cannot create setback for {}, expecting "
                   '"Structure Height Multiplier", or '
                   '"Meters", but got {!r}'
                   .format(county_regulations["County"], setback_type))
            logger.warning(msg)
            warn(msg)
            return None

        return setback


class WindSetbackRegulations(SetbackRegulations):
    """Wind setback regulation setback values. """

    MULTIPLIERS = {'high': 3, 'moderate': 1.1}
    """Named generic multipliers. """

    def __init__(self, hub_height, rotor_diameter, regulations_fpath=None,
                 multiplier=None, generic_setback_dist=None):
        """

        Parameters
        ----------
        hub_height : float | int
            Turbine hub height (m), used along with rotor diameter to
            compute blade tip height which is used to determine setback
            distance.
        rotor_diameter : float | int
            Turbine rotor diameter (m), used along with hub height to
            compute blade tip height which is used to determine setback
            distance.
        regulations_fpath : str | None, optional
            Path to regulations ``.csv`` or ``.gpkg`` file. At a
            minimum, this file must contain the following columns:

                - ``Feature Type``: Contains labels for the type of
                  setback that each row represents. This should be a
                  `"feature_type"` label that can be found in the
                  :attr:`~reVX.exclusions.setbacks.setbacks.SETBACK_SPECS`
                  dictionary (e.g. ``"structures"``, ``"roads"``,
                  ``"water"``, etc.), unless you have created your own
                  setback calculator using
                  :func:`~reVX.exclusions.setbacks.setbacks.setbacks_calculator`,
                  in which case this label can match the `feature_type`
                  input you used for that function call.
                - ``Feature Subtype``: Contains labels for feature
                  subtypes. The feature subtypes are only used for
                  down-selecting the local regulations that should be
                  applied for a particular feature, so often you can
                  leave this blank or set it to ``None``. If you do
                  specify this value, it should be a
                  `"feature_subtypes_to_exclude"` label that can be
                  found in the
                  :attr:`~reVX.exclusions.exclusions.setbacks.setbacks.SETBACK_SPECS`
                  dictionary, unless you have created your own setback
                  calculator using
                  :func:`~reVX.exclusions.setbacks.setbacks.setbacks_calculator`,
                  in which case this label can match the
                  `feature_subtypes_to_exclude` input you used for that
                  function call.
                - ``Value Type``: Specifies wether the value is a
                  multiplier or static height. See below for more info.
                - ``Value``: Numeric value of the setback or multiplier.
                - ``FIPS``: Specifies a unique 5-digit code for each
                  county (this can be an integer - no leading zeros
                  required). This is used to match the county
                  regulations to the county's spatial extent.

                  .. NOTE:: This column is optional if the regulations
                     file already includes a ``geometry`` column that
                     defines the spatial boundaries for each row.

            Valid options for the ``Value Type`` are (case-insensitive;
            dashes, underscores, and spaces are interchangeable):

                - "Max-tip Height Multiplier"
                - "Rotor-Diameter Multiplier"
                - "Hub-height Multiplier"
                - "Meters"

            If this input is ``None``, a generic setback of
            ``max_tip_height * multiplier`` is used.
            By default ``None``.
        multiplier : int | float | str | None, optional
            A setback multiplier to use if regulations are not supplied.
            This multiplier will be applied to the
            ``generic_setback_dist`` to calculate the setback. If
            supplied along with ``regulations_fpath``, this input will
            be used to apply a setback to all counties not listed in the
            regulations file. If this input is a string, it must be a
            key in :attr:`MULTIPLIERS`. By default `None`.
        generic_setback_dist : float | int | None, optional
            Optional generic setback distance. By default, ``None``.
        """
        self._hub_height = hub_height
        self._rotor_diameter = rotor_diameter
        max_tip_height = hub_height + rotor_diameter / 2
        super().__init__(system_height=max_tip_height,
                         regulations_fpath=regulations_fpath,
                         multiplier=multiplier,
                         generic_setback_dist=generic_setback_dist)

    def _preflight_check(self, regulations_fpath):
        """ Run preflight checks on WindSetbackRegulations inputs.

        In addition to the checks performed in `Regulations`, the
        `multiplier` is converted to a float values if a string is
        input.

        Parameters
        ----------
        regulations_fpath : str | None
            Path to wind regulations .csv or .gpkg file, if None create
            global setbacks.
        """
        super()._preflight_check(regulations_fpath)
        if isinstance(self._multi, str):
            self._multi = self.MULTIPLIERS.get(self._multi)
            logger.debug('Computing setbacks using generic Max-tip Height '
                         'Multiplier of {}'.format(self._multi))

    @property
    def hub_height(self):
        """
        Turbine hub height in meters

        Returns
        -------
        float
        """
        return self._hub_height

    @property
    def rotor_diameter(self):
        """
        Turbine rotor diameter in meters

        Returns
        -------
        float
        """
        return self._rotor_diameter

    def _county_regulation_value(self, county_regulations):
        """Retrieve county regulation setback. """
        setback_type = county_regulations["Value Type"]
        setback = float(county_regulations["Value"])
        if setback_type == "max tip height multiplier":
            setback *= self.system_height
        elif setback_type == "rotor diameter multiplier":
            setback *= self.rotor_diameter
        elif setback_type == "hub height multiplier":
            setback *= self.hub_height
        elif setback_type != "meters":
            msg = ('Cannot create setback for {}, expecting '
                   '"Max-tip Height Multiplier", '
                   '"Rotor-Diameter Multiplier", '
                   '"Hub-height Multiplier", or '
                   '"Meters", but got {!r}'
                   .format(county_regulations["County"], setback_type))
            logger.warning(msg)
            warn(msg)
            return
        return setback


def validate_setback_regulations_input(generic_setback_dist=None,
                                       system_config=None):
    """Validate the setback regulations initialization input.

    Callers may provide a dedicated ``generic_setback_dist``
    together with an optional nested ``system_config``. Legacy flat
    inputs are rejected.

    Parameters
    ----------
    generic_setback_dist : float | int | None
        Generic setback distance for the new interface.
        By default, ``None``.
    system_config : dict | None
        Optional nested system configuration. Wind inputs use the
        ``hub_height`` and ``rotor_diameter`` keys. Solar inputs use
        ``pv_system_height``. The setbacks interface does not currently
        consume a ``pv_system_size`` key directly.

    Returns
    -------
    dict
        Normalized setback regulations inputs.

    Raises
    ------
    RuntimeError
        If not enough info is provided or the inputs are ambiguous.
    """
    system_config = system_config or {}
    if not isinstance(system_config, dict):
        raise RuntimeError("`system_config` must be a dictionary if provided.")

    input_hub_height = system_config.get("hub_height")
    input_rotor_diameter = system_config.get("rotor_diameter")
    input_pv_system_height = system_config.get("pv_system_height")

    has_hub_height = input_hub_height is not None
    has_rotor_diameter = input_rotor_diameter is not None
    has_partial_wind_specs = has_hub_height != has_rotor_diameter
    if has_partial_wind_specs:
        raise RuntimeError("Must provide both `hub_height` and "
                           "`rotor_diameter` when using wind system "
                           "specifications.")

    has_wind_specs = has_hub_height and has_rotor_diameter
    if has_wind_specs and input_pv_system_height is not None:
        raise RuntimeError("`system_config` may include either wind "
                           "specifications (`hub_height` and "
                           "`rotor_diameter`) or solar specifications "
                           "(`pv_system_height`), but not both.")

    all_inputs_missing = (generic_setback_dist is None
                          and input_pv_system_height is None
                          and not has_wind_specs)
    if all_inputs_missing:
        raise RuntimeError("Must provide `generic_setback_dist` "
                           "and/or technology-specific values in "
                           "`system_config`.")

    if has_wind_specs:
        return {"hub_height": input_hub_height,
                "rotor_diameter": input_rotor_diameter,
                "generic_setback_dist": generic_setback_dist}

    return {"system_height": input_pv_system_height,
            "generic_setback_dist": generic_setback_dist}


def select_setback_regulations(regulations_fpath=None, multiplier=None,
                               generic_setback_dist=None, system_config=None):
    """Select appropriate setback regulations based on input.

    Parameters
    ----------
    regulations_fpath : str | None, optional
        Path to regulations ``.csv`` or ``.gpkg`` file. At a minimum,
        this file must contain the following columns: ``Feature Type``,
        which contains labels for the type of setback that each row
        represents, ``Value Type``, which specifies whether the value is
        a multiplier or static height, ``Value``, which specifies the
        numeric value of the setback or multiplier, and ``FIPS``, which
        specifies a unique 5-digit code for each county (this can be an
        integer - no leading zeros required). Valid options for the
        ``Value Type`` are (case-insensitive; dashes, underscores,
        and spaces are interchangeable):

            - "Structure Height Multiplier"
            - "Meters"

        If this input is ``None``, a generic setback of
        ``generic_setback_dist * multiplier`` is used. By default
        ``None``.
    multiplier : int | float | str | None, optional
        A setback multiplier to use if regulations are not supplied.
        This multiplier will be applied to the
        ``generic_setback_dist``
        to calculate the setback. If supplied along with
        ``regulations_fpath``, this input will be used to apply a
        setback to all counties not listed in the regulations file.
        By default ``None``.
    generic_setback_dist : float | int | None
        Optional generic fallback setback distance. This can be used
        together with ``system_config`` so that local ordinances resolve
        against technology-specific values while the generic fallback
        uses a separate base distance.
    system_config : dict | None
        Optional nested system configuration. Wind inputs use
        ``hub_height`` and ``rotor_diameter``, which are be used to
        compute setbacks based on those individual quantities as well as
        the max-tip-height. Solar inputs use ``pv_system_height``, which
        is used to compute height-based setbacks.

    Returns
    -------
    Regulations
        A regulations object that can be used to calculate the requested
        setback distance.
    """

    config = validate_setback_regulations_input(
        generic_setback_dist=generic_setback_dist,
        system_config=system_config,
    )

    if _has_wind_specs(config):
        return WindSetbackRegulations(
            regulations_fpath=regulations_fpath,
            multiplier=multiplier,
            **config,
        )

    return SetbackRegulations(
        regulations_fpath=regulations_fpath,
        multiplier=multiplier,
        **config,
    )


def _has_wind_specs(config):
    """bool: Whether wind system specs were provided."""
    return (config.get("hub_height") is not None
            and config.get("rotor_diameter") is not None)
