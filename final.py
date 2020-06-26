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
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
import string
import numpy as np

es_host = "127.0.0.1"
es_port = "9200"

app=Flask(__name__)

url_list=[]
num_word=[]
time=[]
i=0
word_freq=[]

@app.route('/')
@app.route('/result')
def render_file() : 
	global url_list
	global num_word
	global time
	return render_template('upload.html', len=len(url_list), url_list=url_list, num_word=num_word, time=time)

@app.route('/upload', methods=['GET','POST'])
def upload_file() : 
	global url_list
	global time
	global num_word

	if request.method=='GET' :
		dic1={}
		text=request.args['url_text']
		if not text :
			dic1[text]="입력값 없음"
		elif text in url_list : 
			dic1[text]="중복"
		else : 
			url_list.append(text)
			new=[]
			new.append(text)
			search(new)
			dic1[text]="성공"
		return render_template('result.html', dic=dic1)

	elif request.method=='POST' : 
		f=request.files['url_file']
		if not f :
			pass

		else : 
			f.save(secure_filename(f.filename))
			fp=open(f.filename, 'r')
			new=[]
			dic2={}
			while True :
				line=fp.readline().replace("\n", "").replace(" ", "")
				if not line :
					break
				if line in url_list :
					dic2[line]="중복"
					continue;
				url_list.append(line)
				new.append(line)
				dic2[line]="성공"
			fp.close()
			search(new)
			return render_template('result.html', dic=dic2)
	
def search(lst) : 
	global i
	global num_word
	global word_freq	
	
	es = Elasticsearch([{'host':es_host,'port':es_port}],timeout=30)

	stop_words = set(stopwords.words('english'))
	
	for url in lst:
		
		word_d = {}
		word_list=[]		

		res = requests.get(url)
		html = res.text
		soup = BeautifulSoup(html,'html.parser',from_encoding='utf-8')
		for s in soup('script'): s.extract()
		for s in soup('style'): s.extract()
		my_para = soup.select('body div')
		
		result=[]
			
		for para in my_para : 

			sen = para.get_text()
			
			tokenized_text = sent_tokenize(sen)
			
			for t in tokenized_text:
				sentence = word_tokenize(t)
				words = []
				
				for word in sentence:
					words_ = list(filter(str.isalpha,word))
					strA = "".join(words_)
					words.append(strA)
				
				for word in words:
					word = word.lower()
					if word not in stop_words:
						if len(word)>2:
							result.append(word)
		

		for w in result:
			if w not in word_d:
				word_d[w]=1
			else:
				word_d[w]+=1
		result = list(set(result))
	
		count = 0
		for w,c in sorted(word_d.items(),key=lambda x:x[1], reverse=False):
			count += c
		
		num_word.append(count)
		
		top_words = []
		similar_urls = []
	


		word_freq.append(word_d)
		#for value in word_d.values() : 
		#	word_list.append(value)
		#dictionary_copy=word_d.copy()
		#word_list.append(dictionary_copy)

		e = {
			"url":url,
			"words_num":count,
			"top_words":top_words,
			"similar_urls":similar_urls
		}
		res = es.index(index='urls',doc_type='analysis',id=i,body=e)
		
		i+=1
		
		print(res)

	
	return

@app.route('/cossearch', methods=['GET'])
def cosine_analysis() :
	global url_list
	cos_result={}

	if request.method=='GET' : 
		cos_index=int(request.args['cos_index'])
		#stan_url=url_list[cos_index]
		#v_stan=make_vector(cos_index) 	#선택한 링크 벡터 만들어놓음

		for index in range(len(url_list)) : 
			#if index==cos_index : 
			#	pass
			#else : 
				v_com=make_vector(index, cos_index) #호출해서 링크 분석함
				v_stan=make_vector(cos_index, index)
				dotpro=np.dot(v_stan, v_com)
				cossimil=dotpro / (np.linalg.norm(v_stan) * np.linalg.norm(v_com))
				cos_result[url_list[index]]=cossimil
				#result_list.append(cossimil)

	for key, value in cos_result.items() : 
			print(key, value)
	return render_template('upload.html', len=len(url_list), url_list=url_list, num_word=num_word, time=time)

def make_vector(index_stan, index_comp) :
	v=[]

	for w in word_freq[index_comp].keys() : 
		val=0
		for t in word_freq[index_stan].keys() : 
			if t==w :
				val+=1
			v.append(val)

	return v
	

if __name__=='__main__' : 
	app.run(host='127.0.0.1', port=8000, debug=True)
