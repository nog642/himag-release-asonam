#!/bin/bash
# this script must be sourced from python root
(

    # check if virtualenv already exists (it shouldn't)
    workon hds-g 2>/dev/null
    workon_status=$?
    if [ $workon_status -eq 0 ]; then
        exit 4
    fi
    unset workon_status

    mkvirtualenv -p `which python3` hds-g

    workon hds-g  # shouldn't be necessary but doesn't hurt to be sure
    workon_status=$?
    if [ $workon_status -ne 0 ]; then
        echo workon test failed with status $workon_status
        echo exiting...
        exit 3
    fi
    unset workon_status

    pip install --upgrade pip
    pip install -r hds-g-requirements.txt
    pip_status=$?
    if [ $pip_status -ne 0 ]; then
        status=$pip_status
        echo pip install failed with status $pip_status
        echo exiting...
        exit 3
    fi
    unset pip_status

    add2virtualenv .

    exit 0
)
indicator=$?

if [ $indicator -eq 2 ]; then
    echo this script must be sourced from python root
    (exit 1)
elif [ $indicator -eq 3 ]; then
    echo cleaning up...
    rmvirtualenv hds-g
    (exit 1)
elif [ $indicator -eq 4 ]; then
    echo rmvirtualenv your current hds-g virtualenv first
    (exit 1)
else
    workon hds-g
fi
