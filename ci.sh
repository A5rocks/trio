#!/bin/bash

set -ex -o pipefail

# disable warnings about pyright being out of date
# used in test_exports and in check.sh
export PYRIGHT_PYTHON_IGNORE_WARNINGS=1

# Log some general info about the environment
echo "::group::Environment"
uname -a
env | sort
echo "::endgroup::"

# Curl's built-in retry system is not very robust; it gives up on lots of
# network errors that we want to retry on. Wget might work better, but it's
# not installed on azure pipelines's windows boxes. So... let's try some good
# old-fashioned brute force. (This is also a convenient place to put options
# we always want, like -f to tell curl to give an error if the server sends an
# error response, and -L to follow redirects.)
function curl-harder() {
    for BACKOFF in 0 1 2 4 8 15 15 15 15; do
        sleep $BACKOFF
        if curl -fL --connect-timeout 5 "$@"; then
            return 0
        fi
    done
    return 1
}

################################################################
# We have a Python environment!
################################################################

echo "::group::Versions"
python -c "import sys, struct, ssl; print('python:', sys.version); print('version_info:', sys.version_info); print('bits:', struct.calcsize('P') * 8); print('openssl:', ssl.OPENSSL_VERSION, ssl.OPENSSL_VERSION_INFO)"
echo "::endgroup::"

echo "::group::Install dependencies"
python -m pip install -U pip uv -c test-requirements.txt
python -m pip --version
python -m uv --version

python -m uv pip install build

python -m build
wheel_package=$(ls dist/*.whl)
python -m uv pip install "trio @ $wheel_package" -c test-requirements.txt

python -m uv pip install pytest coverage -c test-requirements.txt
echo "::endgroup::"

echo "::group::Setup for tests"

# We run the tests from inside an empty directory, to make sure Python
# doesn't pick up any .py files from our working dir. Might have already
# been created by a previous run.
mkdir empty || true
cd empty

INSTALLDIR=$(python -c "import os, trio; print(os.path.dirname(trio.__file__))")
cp ../pyproject.toml "$INSTALLDIR"  # TODO: remove this

# support subprocess spawning with coverage.py
echo "import coverage; coverage.process_startup()" | tee -a "$INSTALLDIR/../sitecustomize.py"

perl -i -pe 's/-p trio\._tests\.pytest_plugin//' "$INSTALLDIR/pyproject.toml"

echo "::endgroup::"

PYTHONPATH=../tests COVERAGE_PROCESS_START=$(pwd)/../pyproject.toml \
coverage run --rcfile=../pyproject.toml -m \
pytest -ra --junitxml=../test-results.xml \
-p _trio_check_attrs_aliases --verbose --durations=10 \
    -k test_run_in_trio_thread_ki -s \
-p trio._tests.pytest_plugin --run-slow --skip-optional-imports "${INSTALLDIR}"

PYTHONPATH=../tests COVERAGE_PROCESS_START=$(pwd)/../pyproject.toml \
coverage run --rcfile=../pyproject.toml -m \
pytest -ra --junitxml=../test-results.xml \
-p _trio_check_attrs_aliases --verbose --durations=10 \
    -k test_run_in_trio_thread_ki -s \
-p trio._tests.pytest_plugin --run-slow --skip-optional-imports "${INSTALLDIR}"

PYTHONPATH=../tests COVERAGE_PROCESS_START=$(pwd)/../pyproject.toml \
coverage run --rcfile=../pyproject.toml -m \
pytest -ra --junitxml=../test-results.xml \
-p _trio_check_attrs_aliases --verbose --durations=10 \
    -k test_run_in_trio_thread_ki -s \
-p trio._tests.pytest_plugin --run-slow --skip-optional-imports "${INSTALLDIR}"

PYTHONPATH=../tests COVERAGE_PROCESS_START=$(pwd)/../pyproject.toml \
coverage run --rcfile=../pyproject.toml -m \
pytest -ra --junitxml=../test-results.xml \
-p _trio_check_attrs_aliases --verbose --durations=10 \
    -k test_run_in_trio_thread_ki -s \
-p trio._tests.pytest_plugin --run-slow --skip-optional-imports "${INSTALLDIR}"

PYTHONPATH=../tests COVERAGE_PROCESS_START=$(pwd)/../pyproject.toml \
coverage run --rcfile=../pyproject.toml -m \
pytest -ra --junitxml=../test-results.xml \
-p _trio_check_attrs_aliases --verbose --durations=10 \
    -k test_run_in_trio_thread_ki -s \
-p trio._tests.pytest_plugin --run-slow --skip-optional-imports "${INSTALLDIR}"

PYTHONPATH=../tests COVERAGE_PROCESS_START=$(pwd)/../pyproject.toml \
coverage run --rcfile=../pyproject.toml -m \
pytest -ra --junitxml=../test-results.xml \
-p _trio_check_attrs_aliases --verbose --durations=10 \
    -k test_run_in_trio_thread_ki -s \
-p trio._tests.pytest_plugin --run-slow --skip-optional-imports "${INSTALLDIR}"

PYTHONPATH=../tests COVERAGE_PROCESS_START=$(pwd)/../pyproject.toml \
coverage run --rcfile=../pyproject.toml -m \
pytest -ra --junitxml=../test-results.xml \
-p _trio_check_attrs_aliases --verbose --durations=10 \
    -k test_run_in_trio_thread_ki -s \
-p trio._tests.pytest_plugin --run-slow --skip-optional-imports "${INSTALLDIR}"

PYTHONPATH=../tests COVERAGE_PROCESS_START=$(pwd)/../pyproject.toml \
coverage run --rcfile=../pyproject.toml -m \
pytest -ra --junitxml=../test-results.xml \
-p _trio_check_attrs_aliases --verbose --durations=10 \
    -k test_run_in_trio_thread_ki -s \
-p trio._tests.pytest_plugin --run-slow --skip-optional-imports "${INSTALLDIR}"

PYTHONPATH=../tests COVERAGE_PROCESS_START=$(pwd)/../pyproject.toml \
coverage run --rcfile=../pyproject.toml -m \
pytest -ra --junitxml=../test-results.xml \
-p _trio_check_attrs_aliases --verbose --durations=10 \
    -k test_run_in_trio_thread_ki -s \
-p trio._tests.pytest_plugin --run-slow --skip-optional-imports "${INSTALLDIR}"

PYTHONPATH=../tests COVERAGE_PROCESS_START=$(pwd)/../pyproject.toml \
coverage run --rcfile=../pyproject.toml -m \
pytest -ra --junitxml=../test-results.xml \
-p _trio_check_attrs_aliases --verbose --durations=10 \
    -k test_run_in_trio_thread_ki -s \
-p trio._tests.pytest_plugin --run-slow --skip-optional-imports "${INSTALLDIR}"
