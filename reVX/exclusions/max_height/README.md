# Height Restriction Exclusions

``reVX`` supports a ``height_restriction`` mode that excludes regions
when your system height exceeds the allowed maximum height.

Use this mode when your regulations data encodes maximum allowed system
height per jurisdiction, or when you want to apply a generic maximum
allowed height everywhere.

## Required regulations format
For rows that should drive this calculation:
* ``Feature Type`` must be ``"maximum height"`` or ``"maximum turbine height"`` (case-insensitive and ignores dashes, underscores, and spaces)
* ``Value Type`` should be ``"meters"`` (case-insensitive)
* ``Value`` is the allowed maximum system height in meters

## Height input modes
You must provide **exactly one** of the following:
* ``system_height`` (directly)
* Both ``hub_height`` and ``rotor_diameter`` (tip-height computed as ``hub_height + rotor_diameter / 2``)

Unlike normal setbacks, this mode is **local-only**, meaning the
You must also provide at least one regulation source:
* ``generic_height_limit`` for a generic maximum allowed system height
* ``regulations_fpath`` for local jurisdiction-specific limits
* Or both, in which case local jurisdictions override the generic
    behavior within their boundaries

## Minimal config example
```json
{
    "log_level": "INFO",
    "excl_fpath": "/path/to/Exclusions.h5",
    "generic_height_limit": 180,
    "system_height": 210,
}
```

Behavior is strict:
* Generic-only: exclude everywhere when ``system_height > generic_height_limit``
* Local-only: exclude a jurisdiction only when ``system_height > local_max_height``
* Generic + local: start from the generic result, then replace it inside
    local jurisdictions using the local maximum height rule
