#!/bin/bash

audio() {
  curl 'http://216.235.94.14/play?s=kxlu2&d=LIVE365&r=0&membername=&session=1405915359-215869&AuthType=NORMAL&ff=15&app_id=live365%3AMozilla5.0X1&SaneID=99.12.182.152-1405914921365' > "$file" &
}

. lib.sh
