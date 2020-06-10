#! /usr/bin/python
from flask import Flask, redirect, url_for, request, render_template
from werkzeug.utils import secure_filename
app=Flask(__name__)

url_list=[]

@app.route('/')
def render_file() : 
	return render_template('upload.html')

@app.route('/upload', methods=['GET','POST'])
def upload_file() : 
	if request.method=='GET' :
		text=request.args['url_text']
		url_list.append(text)
	elif request.method=='POST' : 
		f=request.files['url_file'] 
		f.save(secure_filename(f.filename))
		fp=open(f.filename, 'r')
		while True :
			line=fp.readline().replace("\n", "").replace(" ", "")
			if not line :
				break
			if line in url_list :
				continue;
			url_list.append(line)
		fp.close()
	return "data : ({})".format(url_list)
		

if __name__=='__main__' : 
	app.run(host='127.0.0.1', port=8000, debug=True)
