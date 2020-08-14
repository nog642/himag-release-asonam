#!/bin/bash
exec "$HOME/jdk1.7.0_79/bin/java" -cp "$(dirname $(readlink -f $0))/genediver.jar" gd.DiverWin
