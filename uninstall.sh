#!/bin/bash

files_dir=$(find /usr/local/ -name "zayde-monitor*")
for file in $files_dir
do
	sudo rm -rf "$file"
done
sudo rm -rf /usr/share/applications/zayde-monitor.desktop
sudo rm -rf /usr/share/zayde-monitor
sudo rm -rf /usr/share/doc/zayde-monitor
sudo rm /usr/share/glib-2.0/schemas/com.github.kendonream.zaydemonitor.gschema.xml
sudo glib-compile-schemas /usr/share/glib-2.0/schemas/
echo "Done"
