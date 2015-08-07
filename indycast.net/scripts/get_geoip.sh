#!/bin/sh
#
# We are looking up people based on their IP address, not trying to get their
# GPS location ... because we only want to present the regional stations ... as in
# if someone is in Los Angeles, showing them radio stations from Tajikistan and Kuala
# Lampur is probably not the most common use-case.
#
set -x 

sudo apt-get -y install geoip-bin xz-utils
[ -e GeoLiteCity.dat ] || wget http://geolite.maxmind.com/download/geoip/database/GeoLiteCity.dat.xz
xz -d GeoLiteCity.dat.xz
