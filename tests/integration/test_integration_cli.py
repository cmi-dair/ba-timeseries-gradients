""" CLI Integration tests. """
# pylint: disable=redefined-outer-name
from __future__ import annotations

import dataclasses
import pathlib
import tempfile
from typing import Any, Generator

import h5py
import nibabel as nib
import numpy as np
import pytest
import pytest_mock
from nibabel import gifti

from ba_timeseries_gradients import cli


@dataclasses.dataclass
class MockParser:
    """A mock parser class used for testing command line interface (CLI) functionality.

    This class is used to simulate the behavior of the `argparse.ArgumentParser` class
    in order to test the CLI functionality of the `ba_timeseries_gradients` package.
    """

    bids_dir: pathlib.Path = pathlib.Path("/path/to/bids")
    output_dir: pathlib.Path = pathlib.Path("/path/to/output")
    analysis_level: str = "group"
    subject: list[str] | None = None
    session: list[str] | None = None
    suffix: str | None = None
    task: list[str] | None = None
    extension: str = ".nii.gz"
    dimensionality_reduction: str = "dm"
    parcellation: str | None = None
    output_format: str = "h5"
    kernel: str = "cosine"
    sparsity: float = 0.1
    n_components: int = 10
    force: bool = False
    verbose: str = "info"
    dry_run: bool = False

    def parse_args(self, *args: Any) -> MockParser:
        """Return self. Required for mocking the parser.parse_args() method."""
        return self


@pytest.fixture
def mock_parser() -> MockParser:
    """Return a mock parser object."""
    return MockParser()


@pytest.fixture
def nifti_data_file() -> Generator[str, None, None]:
    """Return a mock NIfTI temporary data file."""
    data = np.random.rand(10, 10, 10, 10)
    with tempfile.NamedTemporaryFile(suffix=".nii") as file:
        nib.save(nib.Nifti1Image(data, np.eye(4)), file.name)
        yield file.name


@pytest.fixture
def nifti_parcellation_file() -> Generator[str, None, None]:
    """Return a mock NIfTI temporary parcellation file."""
    parcellation = np.ones((10, 10, 10), dtype=np.int32)
    parcellation[5:, :, :] = 2
    parcellation[:5, 5:, :] = 3
    with tempfile.NamedTemporaryFile(suffix=".nii") as file:
        nib.save(nib.Nifti1Image(parcellation, np.eye(4)), file.name)
        yield file.name


@pytest.fixture
def surface_data_file() -> Generator[str, None, None]:
    """Return a mock surface data file."""
    data = np.random.rand(10, 20).astype(np.float32)
    with tempfile.NamedTemporaryFile(suffix=".func.gii") as file:
        gii = gifti.GiftiImage(darrays=[gifti.GiftiDataArray(data)])
        nib.save(gii, file.name)
        yield file.name


@pytest.fixture
def surface_parcellation_file() -> Generator[str, None, None]:
    """Return a mock surface parcellation file."""
    parcellation = np.ones((10,), dtype=np.int32)
    parcellation[4:8] = 2
    parcellation[8:] = 3
    with tempfile.NamedTemporaryFile(suffix=".shape.gii") as file:
        gii = gifti.GiftiImage(darrays=[gifti.GiftiDataArray(parcellation)])
        nib.save(gii, file.name)
        yield file.name


def test_volume_input(
    mocker: pytest_mock.MockerFixture,
    mock_parser: MockParser,
    nifti_data_file: str,
    nifti_parcellation_file: str,
) -> None:
    """Test that the CLI works with a volume input."""
    with tempfile.TemporaryDirectory() as output_dir:
        mock_parser.output_dir = pathlib.Path(output_dir)
        mock_parser.parcellation = nifti_parcellation_file
        mocker.patch(
            "ba_timeseries_gradients.parser.get_parser",
            return_value=mock_parser,
        )
        mocker.patch(
            "ba_timeseries_gradients.cli._get_bids_files",
            return_value=[nifti_data_file],
        )

        cli.main()

        output = pathlib.Path(output_dir) / "gradients.h5"

        output_gradients = np.array(h5py.File(output, "r")["gradients"])
        output_lambdas = np.array(h5py.File(output, "r")["lambdas"])

    assert output_gradients.shape == (3, 2)  # three parcels, two components
    assert output_lambdas.shape == (2,)  # two components


def test_surface_input(
    mocker: pytest_mock.MockerFixture,
    mock_parser: MockParser,
    surface_data_file: str,
    surface_parcellation_file: str,
) -> None:
    """Test that the CLI works with a surface input."""
    with tempfile.TemporaryDirectory() as output_dir:
        mock_parser.output_dir = pathlib.Path(output_dir)
        mock_parser.parcellation = surface_parcellation_file
        mocker.patch(
            "ba_timeseries_gradients.parser.get_parser",
            return_value=mock_parser,
        )
        mocker.patch(
            "ba_timeseries_gradients.cli._get_bids_files",
            return_value=[surface_data_file],
        )

        cli.main()
        output = pathlib.Path(output_dir) / "gradients.h5"

        output_gradients = np.array(h5py.File(output, "r")["gradients"])
        output_lambdas = np.array(h5py.File(output, "r")["lambdas"])

    assert output_gradients.shape == (3, 2)  # three parcels, two components
    assert output_lambdas.shape == (2,)  # two components
