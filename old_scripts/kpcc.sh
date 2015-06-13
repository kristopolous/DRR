#!/bin/bash

audio() {
  curl http://live.scpr.org/kpcclive/ > "$file" &
}

. lib.sh
