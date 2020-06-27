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
import timeit
import math

es_host = "127.0.0.1"
es_port = "9200"

app=Flask(__name__)

url_list=[]
num_word=[]
time=[]
i=0
word_freq=[]
similar_urls=[]

@app.route('/')
@app.route('/result')
def render_file() : 
	global url_list
	global num_word
	global time
	return render_template('upload.html', len=len(url_list), url_list=url_list, num_word=num_word, time=time)

#입력된 URL 불러오기
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
			new=[]
			new.append(text)
			search(new)
			url_list.append(text)
			time.append(0)
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
				time.append(0)
				dic2[line]="성공"
			fp.close()
			search(new)
			return render_template('result.html', dic=dic2)

#URL별 단어 분리 및 저장
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

		word_freq.append(word_d)
	
		similar_urls.append("hi")
		e = {
			"url":url,
			"words_num":count,
		}
		res = es.index(index='urls',doc_type='analysis',id=i,body=e)
		
		i+=1
		
		print(res)

	
	return

#COSINE SIMILARITY 분석
@app.route('/cossearch', methods=['GET'])
def cosine_analysis() :
	global time
	global url_list
	global similar_urls
	global num_word

	cos_result={}
	cos_index=0

	es = Elasticsearch([{'host':es_host,'port':es_port}],timeout=30)
	
	if len(url_list)<2 : 
		message="비교 대상이 충분하지 않습니다"
		return render_template('popup.html', message=message)
	
	if request.method=='GET' : 
		cos_index=int(request.args['cos_index'])
		cos_url=url_list[cos_index]
		
		start_time=timeit.default_timer()

		for index in range(len(url_list)) : 
			if index==cos_index : 
				pass
			else : 
				v_com=make_vector(index, cos_index) #호출해서 링크 분석함
				v_stan=make_vector(cos_index, index)	
				dotpro=np.dot(v_stan, v_com)
				cossimil=dotpro / (np.linalg.norm(v_stan) * np.linalg.norm(v_com))
				cos_result[url_list[index]]=cossimil
			

		terminate_time=timeit.default_timer()
		
		time[cos_index]=round(terminate_time - start_time, 4)
				

	res_result=sorted(cos_result.items(), key=(lambda x:x[1]), reverse=True)

	send_result=[]
	send_index=0

	for key, value in res_result : 
		if send_index>2 : 
			break
		send_result.append(key)
		send_index+=1


	doc=es.get(index='urls', doc_type='analysis', id=cos_index)
	res = es.update(index='urls',doc_type='analysis',id=cos_index,body={'doc':{"similar_urls":send_result}})

	return render_template('cos_result.html', result=send_result)

def make_vector(index_stan, index_comp) :
	v=[]

	for w in word_freq[index_comp].keys() : 
		val=0
		for t in word_freq[index_stan].keys() : 
			if t==w :
				val+=1
			v.append(val)

	return v

#TF_IDF 분석
@app.route('/tisearch',methods=['GET'])
def tfidf_analysis():
	global time
	global url_list
	
	es = Elasticsearch([{'host':es_host,'port':es_port}],timeout=30)

	all_tfidfs = {}
	
	if len(url_list)<2 : 
		message="비교 대상이 충분하지 않습니다"
		return render_template('popup.html', message=message)
	
	if request.method=='GET' : 
		tf_index=int(request.args['tf_index'])

		start_time=timeit.default_timer()

		tf_res = {}
		tfidf_result = []
		
		for w in word_freq[tf_index].keys():
			_tf = tf(tf_index,w) #tf값 계산함수 호출
			_idf = idf(w) #idf값 계산함수 호출
			tf_res[w]=_tf*_idf #tf_idf 결과 저장
		sorted(tf_res.items(), key= lambda x:x[1], reverse=True)
		tfidf_result=list(tf_res.keys())

		all_tfidfs[url_list[tf_index]]=tfidf_result[0:10] 
		
		terminate_time=timeit.default_timer()
		time[tf_index]=round(terminate_time-start_time,4)

	doc=es.get(index='urls', doc_type='analysis', id=tf_index)
	res = es.update(index='urls',doc_type='analysis',id=tf_index,body={'doc':{"top_words":tfidf_result[0:10]}})

	return render_template('tf_result.html',result=tfidf_result[0:10])
	
#tf값 계산
def tf(d,w):
	tfk = word_freq[d]
	_t = tfk[w]
	return _t/float(len(word_freq[d].keys()))

#idf값 계산
def idf(w):
	
	doc_freq = 0
	for idf_index in range(0,len(url_list)):
		if w in word_freq[idf_index].keys():
			doc_freq +=1

	return math.log(len(url_list)/float(doc_freq))
			





if __name__=='__main__' : 
	app.run(host='127.0.0.1', port=8000, debug=True)
