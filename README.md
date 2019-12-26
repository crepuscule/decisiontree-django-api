# decisiontree-django-api
encapsulating C4.5 and CART with django web framework
		master
		   |
old -> github -> server
	     \
	      ->  local

How to Install:
	1. get python3.6 
	2. python -m pip install Django
	2. pip install pymysql
	3. pip install djangorestframework
 	4. go to ~/anaconda3/envs/python3.6/lib/python3.6/site-packages/django/db/backends/mysql/ and vim base.py 
	if version < (1, 3, 13):
		raise ImproperlyConfigured(‘mysqlclient 1.3.13 or newer is required; you have %s.’ % Database.version) 　　
		||
		\/
	if version < (1, 3, 13):
		#raise ImproperlyConfigured(‘mysqlclient 1.3.13 or newer is required; you have %s.’ % Database.version) 　　
		pass	
