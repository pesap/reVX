# -*- coding: utf-8 -*-
"""
Height restriction regulations
"""
from warnings import warn
import logging

from reVX.exclusions.regulations import AbstractBaseRegulations


logger = logging.getLogger(__name__)


class HeightRestrictionRegulations(AbstractBaseRegulations):
    """Regulations for maximum system height restrictions."""

    def __init__(self, system_height, regulations_fpath=None,
                 generic_height_limit=None):
        """Initialize height-restriction regulations.

        Parameters
        ----------
        system_height : float | int
            System height in meters.
        regulations_fpath : str, optional
            Path to local regulations file. By default, ``None``.
        generic_height_limit : float | int, optional
            Generic maximum allowed system height to apply everywhere
            outside jurisdictions with local regulations. By default,
            ``None``.
        """
        self._system_height = float(system_height)
        super().__init__(generic_regulation_value=generic_height_limit,
                         regulations_fpath=regulations_fpath)

    @property
    def system_height(self):
        """float: System height in meters used for comparison."""
        return self._system_height

    def _county_regulation_value(self, county_regulations):
        """Retrieve county maximum allowable height (meters)."""
        value_type = county_regulations["Value Type"]
        if value_type not in {"meters"}:
            msg = ('Cannot create height restriction for {}, expecting '
                   '"Meters" as a "Value Type", but got {!r}'
                   .format(county_regulations.get("County", "unknown"),
                           value_type))
            logger.warning(msg)
            warn(msg)
            return None

        return float(county_regulations["Value"])


def validate_height_regulations_input(system_height=None, hub_height=None,
                                      rotor_diameter=None,
                                      regulations_fpath=None,
                                      generic_height_limit=None):
    """Validate the height regulations initialization input

    Specifically, this function raises an error unless exactly one of
    the following combinations of inputs are provided:

        - system_height
        - hub_height and rotor_diameter

    Parameters
    ----------
    system_height : float | int
       Height of the system being considered. If this input is not
       ``None``, then ``hub_height`` and ``rotor_diameter`` must both be
       ``None``. By default, `None`.
    hub_height : float | int
        Turbine hub height (m), used along with rotor diameter to
        compute blade tip-height which is used as the system height.
        By default, ``None``.
    rotor_diameter : float | int
        Turbine rotor diameter (m), used along with hub height to
        compute blade tip-height which is used as the system height.
        By default, ``None``.
    regulations_fpath : str, optional
        Path to local regulations file. By default, ``None``.
    generic_height_limit : float | int, optional
        Generic maximum allowed system height in meters to apply
        everywhere outside jurisdictions with local regulations.
        By default, ``None``.

    Returns
    -------
    HeightRestrictionRegulations
        A regulations object that can be used to determine where a
        system exceeds the height restriction.

    Raises
    ------
    RuntimeError
        If not enough info is provided (all inputs are ``None``), or too
        much info is given (all inputs are not ``None``).
    """

    has_system_height = system_height is not None
    has_hub_height = hub_height is not None
    has_rotor_diameter = rotor_diameter is not None
    has_tip_inputs = has_hub_height and has_rotor_diameter
    has_partial_tip_input = has_hub_height != has_rotor_diameter

    if has_partial_tip_input:
        raise RuntimeError('Must provide both `hub_height` and '
                           '`rotor_diameter` when using turbine '
                           'specifications for height restrictions.')

    if has_system_height == has_tip_inputs:
        raise RuntimeError('Must provide exactly one of `system_height` '
                           'or (`hub_height` and `rotor_diameter`) for '
                           'height restriction exclusions.')

    if system_height is None:
        system_height = hub_height + rotor_diameter / 2

    return HeightRestrictionRegulations(
        system_height=system_height,
        regulations_fpath=regulations_fpath,
        generic_height_limit=generic_height_limit,
    )
