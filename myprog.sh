#! /bin/bash

if [ ! -d "templates" ]; then
	mkdir templates
fi

if [ -f "cos_result.html" ]; then
	mv cos_result.html templates
fi

if [ -f "popup.html" ]; then
	mv popup.html templates
fi

if [ -f "result.html" ]; then
	mv result.html templates
fi

if [ -f "upload.html" ]; then
	mv upload.html templates
fi

if [ -f "tf_result.html" ]; then
	mv tf_result.html templates
fi

sudo chmod 755 final.py

./final.py


