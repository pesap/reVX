# -*- coding: utf-8 -*-
"""GeoPackage handler tests."""

from pathlib import Path
import shutil

import geopandas as gpd
import pytest
from shapely.geometry import Point

from reVX.handlers.geopackage import GPKGMeta


def _write_geopackage(path, layer_name):
    """Write a single-feature geopackage with a specific layer name."""
    gdf = gpd.GeoDataFrame(
        {"value": [1]}, geometry=[Point(0, 0)], crs="EPSG:4326"
    )

    write_path = path if path.suffix == ".gpkg" else path.with_suffix(".gpkg")
    gdf.to_file(write_path, layer=layer_name, driver="GPKG", index=False)

    if write_path != path:
        shutil.move(write_path, path)


@pytest.mark.parametrize("filename", ["OR.gpkg", "IN.gpkg", "AND.gpk"])
def test_primary_key_column_uses_escaped_table_name(tmp_path, filename):
    """Reserved-word layer names should not break PRAGMA introspection."""
    gpkg_path = tmp_path / filename
    layer_name = Path(filename).stem
    _write_geopackage(gpkg_path, layer_name)

    meta = GPKGMeta(gpkg_path)

    assert meta.primary_table == layer_name
    assert meta.primary_key_column == "fid"
