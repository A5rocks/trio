#!/bin/bash

set -ex -o pipefail

echo "::group::Install dependencies"
python -m pip install -U pip -c test-requirements.txt
python -m pip --version

python -m pip install build

python -m build
wheel_package=$(ls dist/*.whl)
python -m pip install "$wheel_package" -c test-requirements.txt

echo "::endgroup::"

for i in {1..1000}; do
    python repro.py
done
