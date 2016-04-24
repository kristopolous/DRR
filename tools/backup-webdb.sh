#!/bin/sh

fname=`date +"%Y%m%d-%H%M"`.db.lzma
db=4b/main.db
backup=/tmp/backup.lzma
source ../misc/backup-secrets

[ -e $backup ] && rm $backup 
lzma -c 9 $db $backup
if [ -e $backup ]; then
  scp -P $port -i $private_key $backup $username@$host:$path/$fname
  rm $backup
else
  echo "Couldn't make $backup"
fi
