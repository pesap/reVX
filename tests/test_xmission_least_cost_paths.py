# -*- coding: utf-8 -*-
# pylint: disable=all
"""
Least cost transmission line path tests
"""
import json
import os
import shutil
import random
import tempfile
import traceback

import pytest
import rasterio
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import shape, Point
from click.testing import CliRunner

from rex import Outputs
from rex.utilities.loggers import LOGGERS
from reV.handlers.exclusions import ExclusionLayers
from reVX import TESTDATADIR
from reVX.handlers.geotiff import Geotiff
from reVX.least_cost_xmission.config import XmissionConfig
from reVX.least_cost_xmission.least_cost_paths_cli import main
from reVX.least_cost_xmission.least_cost_paths import LeastCostPaths
from reVX.utilities.exceptions import LeastCostPathNotFoundError

COST_H5 = os.path.join(TESTDATADIR, 'xmission', 'xmission_layers.h5')
FEATURES = os.path.join(TESTDATADIR, 'xmission', 'ri_county_centroids.gpkg')
ALLCONNS_FEATURES = os.path.join(TESTDATADIR, 'xmission', 'ri_allconns.gpkg')
ISO_REGIONS_F = os.path.join(TESTDATADIR, 'xmission', 'ri_regions.tif')
CHECK_COLS = ('start_index', 'length_km', 'cost', 'index')
DEFAULT_CONFIG = XmissionConfig()


def _cap_class_to_cap(capacity):
    """Get capacity for a capacity class. """
    capacity_class = DEFAULT_CONFIG._parse_cap_class(capacity)
    return DEFAULT_CONFIG['power_classes'][capacity_class]


def check(truth, test, check_cols=CHECK_COLS):
    """
    Compare values in truth and test for given columns
    """
    if check_cols is None:
        check_cols = truth.columns.values

    truth = truth.sort_values(['start_index', 'index'])
    test = test.sort_values(['start_index', 'index'])

    for c in check_cols:
        msg = f'values for {c} do not match!'
        c_truth = truth[c].values
        c_test = test[c].values
        assert np.allclose(c_truth, c_test, equal_nan=True), msg


@pytest.fixture
def ba_regions_and_network_nodes():
    """Generate test BA regions and network nodes from ISO shapes. """
    with Geotiff(ISO_REGIONS_F) as gt:
        iso_regions = gt.values[0].astype('uint16')
        profile = gt.profile

    s = rasterio.features.shapes(iso_regions, transform=profile['transform'])
    ba_str, shapes = zip(*[("p{}".format(int(v)), shape(p))
                           for p, v in s if int(v) != 0])

    state = ["Rhode Island"] * len(ba_str)
    ri_ba = gpd.GeoDataFrame({"ba_str": ba_str, "state": state},
                             crs=profile['crs'],
                             geometry=list(shapes))

    ri_network_nodes = ri_ba.copy()
    ri_network_nodes.geometry = ri_ba.centroid
    return ri_ba, ri_network_nodes


@pytest.fixture(scope="module")
def runner():
    """
    cli runner
    """
    return CliRunner()


@pytest.mark.parametrize('capacity', [100, 200, 400, 1000, 3000])
def test_capacity_class(capacity):
    """
    Test least cost xmission and compare with baseline data
    """
    truth = os.path.join(TESTDATADIR, 'xmission',
                         f'least_cost_paths_{capacity}MW.csv')
    cost_layer = f'tie_line_costs_{_cap_class_to_cap(capacity)}MW'
    test = LeastCostPaths.run(COST_H5, FEATURES, [cost_layer])

    if not os.path.exists(truth):
        test.to_csv(truth, index=False)

    truth = pd.read_csv(truth)

    check(truth, test)


@pytest.mark.parametrize('max_workers', [1, None])
def test_parallel(max_workers):
    """
    Test least cost xmission and compare with baseline data
    """
    capacity = random.choice([100, 200, 400, 1000, 3000])
    truth = os.path.join(TESTDATADIR, 'xmission',
                         f'least_cost_paths_{capacity}MW.csv')
    cost_layer = f'tie_line_costs_{_cap_class_to_cap(capacity)}MW'
    test = LeastCostPaths.run(COST_H5, FEATURES, [cost_layer],
                              max_workers=max_workers)

    if not os.path.exists(truth):
        test.to_csv(truth, index=False)

    truth = pd.read_csv(truth)

    check(truth, test)


def test_clip_buffer():
    """Test using clip buffer for points that would otherwise be cut off. """
    with tempfile.TemporaryDirectory() as td:
        out_cost_fp = os.path.join(td, "costs.h5")
        out_features_fp = os.path.join(td, "feats.gpkg")
        shutil.copy(COST_H5, out_cost_fp)
        gpd.GeoDataFrame(data={"index": [0, 1]},
                         geometry=[Point(-70.868065, 40.85588),
                                   Point(-71.9096, 42.016506)],
                         crs="EPSG:4326").to_file(out_features_fp,
                                                  driver="GPKG")

        costs = np.ones(shape=(1434, 972))
        costs[0, 3] = costs[1, 3] = costs[2, 3] = costs[3, 3] = -1
        costs[3, 1] = costs[3, 2] = -1

        with Outputs(out_cost_fp, "a") as out:
            out['tie_line_costs_102MW'] = costs

        with ExclusionLayers(out_cost_fp) as excl:
            assert np.allclose(excl['tie_line_costs_102MW'], costs)

        out_no_buffer = LeastCostPaths.run(out_cost_fp, out_features_fp,
                                           ["tie_line_costs_102MW"],
                                           max_workers=1)
        assert out_no_buffer["length_km"].isna().all()

        out = LeastCostPaths.run(out_cost_fp, out_features_fp,
                                 ["tie_line_costs_102MW"], max_workers=1,
                                 clip_buffer=10)
        assert (out["length_km"] > 193).all()


@pytest.mark.parametrize("save_paths", [False, True])
def test_cli(runner, save_paths):
    """
    Test CostCreator CLI
    """
    capacity = random.choice([100, 200, 400, 1000, 3000])
    cost_layer = f'tie_line_costs_{_cap_class_to_cap(capacity)}MW'
    truth = os.path.join(TESTDATADIR, 'xmission',
                         f'least_cost_paths_{capacity}MW.csv')
    truth = pd.read_csv(truth)

    with tempfile.TemporaryDirectory() as td:
        config = {
            "log_directory": td,
            "execution_control": {
                "option": "local",
            },
            "cost_fpath": COST_H5,
            "features_fpath": FEATURES,
            "save_paths": save_paths,
            "cost_layers": [cost_layer]
        }
        config_path = os.path.join(td, 'config.json')
        with open(config_path, 'w') as f:
            json.dump(config, f)

        result = runner.invoke(main, ['from-config',
                                      '-c', config_path, '-v'])
        msg = ('Failed with error {}'
               .format(traceback.print_exception(*result.exc_info)))
        assert result.exit_code == 0, msg

        if save_paths:
            test = '{}_lcp.gpkg'.format(os.path.basename(td))
            test = os.path.join(td, test)
            test = gpd.read_file(test)
            assert test.geometry is not None
        else:
            test = '{}_lcp.csv'.format(os.path.basename(td))
            test = os.path.join(td, test)
            test = pd.read_csv(test)
        check(truth, test)

    LOGGERS.clear()


@pytest.mark.parametrize("save_paths", [False, True])
def test_reinforcement_cli(runner, ba_regions_and_network_nodes, save_paths):
    """
    Test Reinforcement cost routines and CLI
    """
    ri_ba, ri_network_nodes = ba_regions_and_network_nodes
    ri_feats = gpd.clip(gpd.read_file(ALLCONNS_FEATURES), ri_ba.buffer(10_000))

    with tempfile.TemporaryDirectory() as td:
        ri_feats_path = os.path.join(td, 'ri_feats.gpkg')
        ri_feats.to_file(ri_feats_path, driver="GPKG", index=False)

        ri_ba_path = os.path.join(td, 'ri_ba.gpkg')
        ri_ba.to_file(ri_ba_path, driver="GPKG", index=False)

        ri_network_nodes_path = os.path.join(td, 'ri_network_nodes.gpkg')
        ri_network_nodes.to_file(ri_network_nodes_path, driver="GPKG",
                                 index=False)

        ri_substations_path = os.path.join(td, 'ri_subs.gpkg')
        result = runner.invoke(main,
                               ['map-ss-to-rr',
                                '-feats', ri_feats_path,
                                '-regs', ri_ba_path,
                                '-rid', "ba_str",
                                '-of', ri_substations_path])
        msg = ('Failed with error {}'
               .format(traceback.print_exception(*result.exc_info)))
        assert result.exit_code == 0, msg

        assert "ri_subs.gpkg" in os.listdir(td)
        ri_subs = gpd.read_file(ri_substations_path)
        assert len(ri_subs) < len(ri_feats)
        assert (ri_subs["category"] == "Substation").all()
        counts = ri_subs["ba_str"].value_counts()

        assert (counts.index == ['p4', 'p1', 'p3', 'p2']).all()
        assert (counts == [50, 34, 10, 5]).all()

        config = {
            "log_directory": td,
            "execution_control": {
                "option": "local",
            },
            "cost_fpath": COST_H5,
            "features_fpath": ri_substations_path,
            "network_nodes_fpath": ri_network_nodes_path,
            "transmission_lines_fpath": ALLCONNS_FEATURES,
            "region_identifier_column": "ba_str",
            "capacity_class": 400,
            "cost_layers": ["tie_line_costs_{}MW"],
            "barrier_mult": 100,
            "save_paths": save_paths
        }
        config_path = os.path.join(td, 'config.json')
        with open(config_path, 'w') as f:
            json.dump(config, f)

        result = runner.invoke(main, ['from-config',
                                      '-c', config_path, '-v'])
        msg = ('Failed with error {}'
               .format(traceback.print_exception(*result.exc_info)))
        assert result.exit_code == 0, msg

        if save_paths:
            test = '{}_lcp.gpkg'.format(os.path.basename(td))
            test = os.path.join(td, test)
            test = gpd.read_file(test)
            assert test.geometry is not None
        else:
            test = '{}_lcp.csv'.format(os.path.basename(td))
            test = os.path.join(td, test)
            test = pd.read_csv(test)

        assert "reinforcement_poi_lat" in test
        assert "reinforcement_poi_lon" in test
        assert "poi_lat" not in test
        assert "poi_lon" not in test
        assert "ba_str" in test

        assert len(test) == 69
        assert np.isclose(test.reinforcement_cost_per_mw.min(), 3332.695,
                          atol=0.001)
        assert np.isclose(test.reinforcement_dist_km.min(), 1.918, atol=0.001)
        assert np.isclose(test.reinforcement_dist_km.max(), 80.353, atol=0.001)
        assert len(test["reinforcement_poi_lat"].unique()) == 4
        assert len(test["reinforcement_poi_lon"].unique()) == 4
        assert np.isclose(test.reinforcement_cost_per_mw.max(), 569757.740,
                          atol=0.001)

    LOGGERS.clear()


def test_reinforcement_cli_single_tline_coltage(runner,
                                                ba_regions_and_network_nodes):
    """
    Test Reinforcement cost routines when tlines have only a single voltage
    """
    ri_ba, ri_network_nodes = ba_regions_and_network_nodes
    ri_feats = gpd.clip(gpd.read_file(ALLCONNS_FEATURES), ri_ba.buffer(10_000))

    with tempfile.TemporaryDirectory() as td:
        ri_feats_path = os.path.join(td, 'ri_feats.gpkg')
        ri_feats.to_file(ri_feats_path, driver="GPKG", index=False)

        ri_ba_path = os.path.join(td, 'ri_ba.gpkg')
        ri_ba.to_file(ri_ba_path, driver="GPKG", index=False)

        ri_network_nodes_path = os.path.join(td, 'ri_network_nodes.gpkg')
        ri_network_nodes.to_file(ri_network_nodes_path, driver="GPKG",
                                 index=False)

        ri_substations_path = os.path.join(td, 'ri_subs.gpkg')
        result = runner.invoke(main,
                               ['map-ss-to-rr',
                                '-feats', ri_feats_path,
                                '-regs', ri_ba_path,
                                '-rid', "ba_str",
                                '-of', ri_substations_path])
        msg = ('Failed with error {}'
               .format(traceback.print_exception(*result.exc_info)))
        assert result.exit_code == 0, msg

        assert "ri_subs.gpkg" in os.listdir(td)
        ri_subs = gpd.read_file(ri_substations_path)
        assert len(ri_subs) < len(ri_feats)
        assert (ri_subs["category"] == "Substation").all()
        counts = ri_subs["ba_str"].value_counts()

        assert (counts.index == ['p4', 'p1', 'p3', 'p2']).all()
        assert (counts == [50, 34, 10, 5]).all()

        ri_tlines_path = os.path.join(td, 'ri_tlines.gpkg')
        tlines = gpd.read_file(ALLCONNS_FEATURES)
        tlines["voltage"] = 138
        tlines.to_file(ri_tlines_path, driver="GPKG", index=False)

        config = {
            "log_directory": td,
            "execution_control": {
                "option": "local",
            },
            "cost_fpath": COST_H5,
            "features_fpath": ri_substations_path,
            "network_nodes_fpath": ri_network_nodes_path,
            "transmission_lines_fpath": ri_tlines_path,
            "region_identifier_column": "ba_str",
            "capacity_class": 400,
            "cost_layers": ["tie_line_costs_{}MW"],
            "barrier_mult": 100,
            "save_paths": False,
        }
        config_path = os.path.join(td, 'config.json')
        with open(config_path, 'w') as f:
            json.dump(config, f)

        result = runner.invoke(main, ['from-config',
                                      '-c', config_path, '-v'])
        msg = ('Failed with error {}'
               .format(traceback.print_exception(*result.exc_info)))
        assert result.exit_code == 0, msg

        test = '{}_lcp.csv'.format(os.path.basename(td))
        test = os.path.join(td, test)
        test = pd.read_csv(test)

        assert "reinforcement_poi_lat" in test
        assert "reinforcement_poi_lon" in test
        assert "poi_lat" not in test
        assert "poi_lon" not in test
        assert "ba_str" in test

        assert len(test) == 69
        assert len(test["reinforcement_poi_lat"].unique()) == 4
        assert len(test["reinforcement_poi_lon"].unique()) == 4

    LOGGERS.clear()


def execute_pytest(capture='all', flags='-rapP'):
    """Execute module as pytest with detailed summary report.

    Parameters
    ----------
    capture : str
        Log or stdout/stderr capture option. ex: log (only logger),
        all (includes stdout/stderr)
    flags : str
        Which tests to show logs and results for.
    """

    fname = os.path.basename(__file__)
    pytest.main(['-q', '--show-capture={}'.format(capture), fname, flags])


if __name__ == '__main__':
    execute_pytest()
