#! /usr/bin/python
from flask import Flask, redirect, url_for, request, render_template
from werkzeug.utils import secure_filename
import re, requests
from bs4 import BeautifulSoup
import operator
from elasticsearch import Elasticsearch
import nltk
from nltk import punkt
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import string

es_host = "127.0.0.1"
es_port = "9200"

app=Flask(__name__)

url_list=[]

num_word=[]
time=[]
i=0

@app.route('/')
def render_file() : 
	return render_template('upload.html', len=0, url_list=url_list, num_word=num_word, time=time)

@app.route('/upload', methods=['GET','POST'])
def upload_file() : 
	if request.method=='GET' :
		text=request.args['url_text']
		if not text :
			pass
		elif text in url_list : 
			pass
		else : 
			url_list.append(text)
			new=[]
			new.append(text)
			search(new)
	elif request.method=='POST' : 
		f=request.files['url_file']
		if not f :
			pass

		else : 
			f.save(secure_filename(f.filename))
			fp=open(f.filename, 'r')
			new=[]
			while True :
				line=fp.readline().replace("\n", "").replace(" ", "")
				if not line :
					break
				if line in url_list :
					continue;
				url_list.append(line)
				new.append(line)
			fp.close()
			search(new)
	return render_template("upload.html", len=len(url_list), url_list=url_list, num_word=num_word, time=time)
	
def search(lst) : 
	global i
		
	es = Elasticsearch([{'host':es_host,'port':es_port}],timeout=30)

	stop_words = set(stopwords.words('english'))
	
	for url in url_list:
		
		word_d = {}

		res = requests.get(url)
		html = res.text
		soup = BeautifulSoup(html,'html.parser',from_encoding='utf-8')
		for s in soup('script'): s.extract()
		for s in soup('style'): s.extract()
		my_para = soup.select('body div')
		
			
		for para in my_para : 

			sen = para.get_text()
			sen = sen.lower().replace(',',' ').replace('.',' ')
			#translator = str.maketrans('','',string.punctuation)
			#sen = sen.translate(translator)
			sen = re.sub('[^0-9a-zA-Zㄱ-힗]', '', sen)
	
			tokens = word_tokenize(sen)
						
			words = []
			for word in tokens:
				word = str(filter(str.isalpha,word))
				words.append(word)
	
			wlist = [k for k in words if not k in stop_words]
			#wlist = sen.split()

			for w in wlist:
				if w not in word_d:
					word_d[w]=1
				word_d[w]+=1
	
		count = 0
		for w,c in sorted(word_d.items(),key=lambda x:x[1], reverse=False):
			count += c
		num_word.append(count)
		
		top_words = []
		similar_urls = []

		e = {
			"url":url,
			"words_num":count,
			"words":word_d,
			"top_words":top_words,
			"similar_urls":similar_urls
		}
		res = es.index(index='urls',doc_type='analysis',id=i,body=e)
		
		i+=1
		
		print(res)

	
	return
		

if __name__=='__main__' : 
	app.run(host='127.0.0.1', port=8000, debug=True)
