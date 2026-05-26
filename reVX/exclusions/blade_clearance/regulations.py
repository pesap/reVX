# -*- coding: utf-8 -*-
"""
Blade clearance regulations
"""
from warnings import warn
import logging

from reVX.exclusions.regulations import AbstractBaseRegulations


logger = logging.getLogger(__name__)


class BladeClearanceRegulations(AbstractBaseRegulations):
    """Regulations for minimum blade clearance restrictions."""

    def __init__(self, hub_height, rotor_diameter, regulations_fpath=None,
                 generic_minimum_clearance=None):
        """Initialize blade clearance regulations.

        Parameters
        ----------
        hub_height : float | int
            Turbine hub height (m), used along with rotor diameter to
            compute blade clearance.
        rotor_diameter : float | int
            Turbine rotor diameter (m), used along with hub height to
            compute blade clearance.
        regulations_fpath : str, optional
            Path to local regulations file. By default, ``None``.
        generic_minimum_clearance : float | int, optional
            Generic minimum blade clearance requirement in meters to
            apply everywhere outside jurisdictions with local
            regulations. By default, ``None``.
        """
        self._hub_height = float(hub_height)
        self._rotor_diameter = float(rotor_diameter)
        super().__init__(generic_regulation_value=generic_minimum_clearance,
                         regulations_fpath=regulations_fpath)

    @property
    def tip_height(self):
        """float: Tip height of the turbine in meters"""
        return self._hub_height + self._rotor_diameter / 2

    @property
    def blade_clearance(self):
        """float: Blade clearance of the turbine in meters"""
        return self._hub_height - self._rotor_diameter / 2

    def _county_regulation_value(self, county_regulations):
        """Retrieve county minimum blade clearance (meters)."""
        value_type = county_regulations["Value Type"]
        value = float(county_regulations["Value"])

        if value_type in {"percent", "percent of tower height"}:
            return self.tip_height * value / 100

        if value_type not in {"meters"}:
            msg = ('Cannot create blade clearance exclusion for {}, expecting '
                   '"Meters", "Percent", or "Percent of Tower Height" as a '
                   '"Value Type", but got {!r}'
                   .format(county_regulations.get("County", "unknown"),
                           value_type))
            logger.warning(msg)
            warn(msg)
            return None

        return value


def validate_blade_clearance_regulations_input(hub_height=None,
                                               rotor_diameter=None,
                                               regulations_fpath=None,
                                               generic_minimum_clearance=None):
    """Validate the blade clearance initialization input

    Parameters
    ----------
    hub_height : float | int
        Turbine hub height (m), used along with rotor diameter to
        compute blade clearance. By default, ``None``.
    rotor_diameter : float | int
        Turbine rotor diameter (m), used along with hub height to
        compute blade clearance. By default, ``None``.
    regulations_fpath : str, optional
        Path to local regulations file. By default, ``None``.
    generic_minimum_clearance : float | int, optional
        Generic minimum blade clearance requirement in meters. By
        default, ``None``.

    Returns
    -------
    BladeClearanceRegulations
        A regulations object that can be used to determine where a
        system does not meet the minimum blade clearance restriction.

    Raises
    ------
    RuntimeError
        If not enough info is provided (all inputs are ``None``), or too
        much info is given (all inputs are not ``None``).
    """

    has_hub_height = hub_height is not None
    has_rotor_diameter = rotor_diameter is not None
    has_tip_inputs = has_hub_height and has_rotor_diameter
    has_partial_tip_input = has_hub_height != has_rotor_diameter

    if not has_tip_inputs or has_partial_tip_input:
        raise RuntimeError('Must provide both `hub_height` and '
                           '`rotor_diameter` when using turbine '
                           'specifications for blade clearance restrictions.')

    return BladeClearanceRegulations(
        hub_height=hub_height,
        rotor_diameter=rotor_diameter,
        regulations_fpath=regulations_fpath,
        generic_minimum_clearance=generic_minimum_clearance,
    )
