#!/bin/bash

set -ex -o pipefail

echo "::group::Install dependencies"
python -m pip install -U pip uv -c test-requirements.txt
python -m pip --version
python -m uv --version

python -m uv pip install build

python -m build
wheel_package=$(ls dist/*.whl)
python -m uv pip install "trio @ $wheel_package" -c test-requirements.txt

python -m uv pip install coverage -c test-requirements.txt
echo "::endgroup::"

echo "::group::Setup for tests"
INSTALLDIR=$(python -c "import os, trio; print(os.path.dirname(trio.__file__))")
cp pyproject.toml "$INSTALLDIR"  # TODO: remove this

# support subprocess spawning with coverage.py
echo "import coverage; coverage.process_startup()" | tee -a "$INSTALLDIR/../sitecustomize.py"

echo "::endgroup::"

for i in {1..100}; do
    COVERAGE_PROCESS_START=$(pwd)/pyproject.toml \
    coverage run --rcfile=pyproject.toml \
    repro.py
done
