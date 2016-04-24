#!/bin/sh

fname_base=`date +"%Y%m%d-%H%M"`

source ../misc/backup-secrets

scp -i $private_key db/main.db $username@$host:$path/$fname
