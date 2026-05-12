#!/bin/bash

files_dir=$(find /usr/local/ -name "z-mon*")
for file in $files_dir
do
	sudo rm -rf "$file"
done
sudo rm -rf /usr/share/applications/z-mon.desktop
sudo rm -rf /usr/share/z-mon
sudo rm -rf /usr/share/doc/z-mon
sudo rm /usr/share/glib-2.0/schemas/com.github.kendonream17.zmon.gschema.xml
sudo glib-compile-schemas /usr/share/glib-2.0/schemas/
echo "Done"
