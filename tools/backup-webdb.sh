#!/bin/bash
dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
base=`dirname $dir`
fname=`date +"%Y%m%d-%H%M"`.db.lzma
db=$base/db/main.db
backup=/tmp/backup.lzma
if [ ! -e $base/misc/backup-secrets.ini ]; then
  echo "Erorr, $base/misc/backup-secrets.ini needs to exist."
  exit -1
fi

source $base/misc/backup-secrets.ini

rm -f $backup 
lzma -9 -c $db > $backup

if [ -e $backup ]; then
  scp -P $port -i $private_key $backup $username@$host:$path/$fname
  rm $backup
else
  echo "Couldn't make $backup"
fi
