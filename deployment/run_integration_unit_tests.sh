#!/bin/bash
#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#

# This script must be executed from the package root directory

set -e

if [ ! -d "testing-venv" ]; then
    echo "Creating testing-venv..."
    python3 -m venv testing-venv
fi


echo "  ---- Rebuilding package locally before testing..."
source testing-venv/bin/activate
echo "  ---- Using python: `type python3`"
echo "  ---- Python version: `python3 --version`"
echo "  ---- Installing pip"
pip3 install --quiet -U pip
echo "  ---- Installing dependency"
source_code="$PWD"
pip install -r ./source/integrations/integration_unit_tests/requirements.txt
echo "  ---- Changing working directory to the test directory"
cd source/integrations/integration_unit_tests/
echo "Updating source path $source_code"
replace="s#%%SOURCE_PATH%%#$source_code#g"
tox_path="$PWD/tox.ini"
echo "tox.ini path: $tox_path"
if [[ "$OSTYPE" == "darwin"* ]]; then
  sed -i '' -e $replace $tox_path
else
  sed -i -e $replace $tox_path
fi

echo "  ---- Running tests..."
coverage run -m unittest discover -p "test_*.py"
echo "  ---- Please make sure all the test cases above pass"
echo
echo
echo "  ---- Waiting for 1 minutes for coverage journaling to complete."
sleep 60
echo
echo "  ---- Combining coverage file for multiprocessing..."
coverage combine
echo "  ---- Unit test Coverage report"
coverage report
coverage xml -o./coverage/coverage.xml
deactivate
echo "Removing source path $source_code"
replace="s#$source_code#%%SOURCE_PATH%%#g"
if [[ "$OSTYPE" == "darwin"* ]]; then
  sed -i '' -e $replace $tox_path
else
  sed -i -e $replace $tox_path
fi
echo "------------------------------------------------------------------------------"
echo "[Unit Tests] Integrations Unit Tests Complete"
echo "------------------------------------------------------------------------------"