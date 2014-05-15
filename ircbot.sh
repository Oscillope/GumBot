#!/bin/sh

echo "Initiating..."

while :
do

   date --rfc-3339=seconds | sed -r -e "s/(.*)/\1 STARTED/"
   DISPLAY=":0" python2 skype2irc.py
   date --rfc-3339=seconds | sed -r -e "s/(.*)/\1 STOPPED/"
   sleep 10

done
