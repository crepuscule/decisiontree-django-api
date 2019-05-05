# 使用Django开发决策树系统后端接口应用文档
>contents
1. 创建Django新项目和新应用
2. 创建模型
3. 后台管理
4. 接口设计
x. 参考

## 创建Django新项目和新应用
`django-admin startproject DecisionTreePredictionSystem`
进入manage.py所在的目录使用命令
`python manage.py startapp weixinapi`创建一个新的应用
最后生成的项目目录结构如图所示：
```
└── DecisionTreePredictionSystem
    ├── DecisionTreePredictionSystem
    │   ├── __init__.py
    │   ├── __pycache__
    │   ├── settings.py
    │   ├── urls.py
    │   └── wsgi.py
    ├── manage.py
    └── weixinapi
        ├── admin.py
        ├── apps.py
        ├── __init__.py
        ├── migrations
        ├── models.py
        ├── tests.py
        ├── urls.py
        └── views.py
```
生成后的应用只有添加到项目中才可以使用，在settings.py中这样设置:
```
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'weixinapi',
]
```
## 创建模型
1. 先设置使用mysql数据库

打开`DecisionTreePredictionSystem/settings.py`设置使用的数据库，即：
```
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'db_weixin',
        'USER': 'root',
        'PASSWORD': '12345678',
        'HOST': '127.0.0.1',
        'PORT': '3306',
    }
}
```

2. 下面开始创建模型

DataSet,Tree,Analysis
1dataSet对应多个Tree
1Tree对应1个DataSet
=> Tree中一对多字段

1tree对应多个Analysis
1Analysis对应1个tree
=> Analysis中一对多字段

1dataset对应1个analysis对应
多个analysis对应1个dataset
=> anslysis中一对多字段
```
class dataSet(models.Model):
    dataSet_id = models.AutoField(primary_key=True)
    dataSet_name = models.CharField(max_length= models.200)
    dataSet_type = models.CharField(max_length= models.200)
    table_name = models.CharField(max_length= models.200)
    size = models.IntegerField(default=0)
    #  DateTimeField.auto_now 这个参数的默认值为false，设置为true时，能够在保存该字段时，将其值设置为当前时间，并且每次修改model，都会自动更新
    # DateTimeField.auto_now_add 个参数的默认值也为False，设置为True时，会在model对象第一次被创建时，将字段的值设置为创建时的时间，以后修改对象时，字段的值不会再更新。
    #如何将创建时间设置为“默认当前”并且可修改:既希望在对象的创建时间默认被设置为当前值，又希望能在日后修改它。 EG: add_date = models.DateTimeField('保存日期',default = timezone.now)
    create_time = models.DateTimeField(default=timezone.now)
 
class Tree(models.Model):
    tree_id = models.AutoField(primary_key=True)
    #null和blank不设置时默认设置为False. null 是针对数据库而言，如果 null=True, 表示数据库的该字段可以为空。blank 是针对表单的，如果 blank=True，表示你的表单填写该字段的时候可以不填
    #dataSet_id = models.IntegerField(blank=False,null=False)
    dataSet = models.ForeignKey(DataSet,on_delete=models.PROTECT)
    tree_name = models.CharField(max_length= models.200)
    tree_type = models.CharField(max_length= models.200)
    optimize_type = models.CharField(max_length= models.200,null=True)
    tree_dict = models.TextField()
    detpth = models.IntegerField(default=0)
    nodes_num = models.IntegerField(default=0)
    create_time = models.DateTimeField(default=timezone.now)
 
class Analysis(models.Model):
    analysis_id = models.AutoField(primary_key=True)
    #tree_id = models.IntegerField(blank=False,null=False)
    tree = models.ForeignKey(Tree,on_delete=models.PROTECT)
    #dataSet_id = models.IntegerField(blank=False,null=False)
    dataSet = models.ForeignKey(DataSet,on_delete=models.PROTECT)
    analysis_name = models.CharField(max_length= models.200)
    accuracy = models.FloatField()
    ifthen = models.TextField()
    content = models.TextField()
    create_time = models.DateTimeField(default=timezone.now)
```
3. 运行数据迁移

运行命令`python manage.py makemigrations weixinapi`生成/migrations/0001_initial.py 迁移文件
此时可以使用命令`python manage.py sqlmigrate polls 0001`查看迁移使用到的数据库SQL语句
```
001
BEGIN;
--
-- Create model DataSet
--
CREATE TABLE `weixinapi_dataset` (`dataSet_id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `dataSet_name` varchar(200) NOT NULL, `dataSet_type` varchar(200) NOT NULL, `table_name` varchar(200) NOT NULL, `size` integer NOT NULL, `create_time` datetime(6) NOT NULL);
--
-- Create model Tree
--
CREATE TABLE `weixinapi_tree` (`tree_id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `tree_name` varchar(200) NOT NULL, `tree_type` varchar(200) NOT NULL, `optimize_type` varchar(200) NULL, `tree_dict` longtext NOT NULL, `detpth` integer NOT NULL, `nodes_num` integer NOT NULL, `create_time` datetime(6) NOT NULL, `dataSet_id` integer NOT NULL);
--
-- Create model Analysis
--
CREATE TABLE `weixinapi_analysis` (`analysis_id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `analysis_name` varchar(200) NOT NULL, `accuracy` double precision NOT NULL, `ifthen` longtext NOT NULL, `content` longtext NULL, `create_time` datetime(6) NOT NULL, `dataSet_id` integer NOT NULL, `tree_id` integer NOT NULL);
ALTER TABLE `weixinapi_tree` ADD CONSTRAINT `weixinapi_tree_dataSet_id_d065b200_fk_weixinapi` FOREIGN KEY (`dataSet_id`) REFERENCES `weixinapi_dataset` (`dataSet_id`);
ALTER TABLE `weixinapi_analysis` ADD CONSTRAINT `weixinapi_analysis_dataSet_id_a7cf9530_fk_weixinapi` FOREIGN KEY (`dataSet_id`) REFERENCES `weixinapi_dataset` (`dataSet_id`);
ALTER TABLE `weixinapi_analysis` ADD CONSTRAINT `weixinapi_analysis_tree_id_ace3725e_fk_weixinapi_tree_tree_id` FOREIGN KEY (`tree_id`) REFERENCES `weixinapi_tree` (`tree_id`);
COMMIT;

```
再运行命令`python manage.py migrate`执行迁移

## 后台管理
django自带的后台管理在开发中能起到很大的帮助作用，现在先注册管理系统帐号并在其中注册相关模型：
```
python manage.py createsuperuser
Username (leave blank to use 'crepuscule'): 
Email address: twilight_wang@163.com
Password: crepuscule
Password (again): crepuscule
The password is too similar to the username.
Bypass password validation and create user anyway? [y/N]: y
Superuser created successfully.
```
接着要注册模型类，以让django能在管理页面显示想要的模型
```
class DataSetAdmin(admin.ModelAdmin):
    list_display = ["dataSet_id","dataSet_name","dataSet_type","dataSet_type","size","create_time"]

class TreeAdmin(admin.ModelAdmin):
    list_display = ["tree_id","tree_name","tree_type","optimize_type","tree_dict","detpth","nodes_num","create_time"]

class AnalysisAdmin(admin.ModelAdmin):
    list_display = ["analysis_id","analysis_name","accuracy","ifthen","content","create_time"]

admin.site.register(DataSet,DataSetAdmin)
admin.site.register(Tree,TreeAdmin)
admin.site.register(Analysis,AnalysisAdmin)
```


## 接口设计
详见api接口设计文档
                     


>参考：
[django模型常用的字段ORM](https://blog.csdn.net/antian1991/article/details/80659169)
AutoField 自动增值的id字段
primary_key=True 为必设置选项
BigAutoField 自动增值的id字段
支持 1 到 9223372036854775807，之间的序号
BigIntegerField 长整形字段
从 -9223372036854775808 到9223372036854775807 的整数
BinaryField 二进制字段
存储内存二进制数据，以 python bytes 对象来访问
BooleanField 布尔值字段
如果许可空的布尔值输入，换用 NullBooleadField
CharField可变长字符串字段
max_length 有最大输入选项为必须设置的选项
DateField日期字段
auto_now：每一次保存对象时，Django 都会自动将该字段的值设置为当前时间。一般用来表示 "最后修改" 时间。要注意使用的是当前日期，而并非默认值，所以
不能通过重写默认值的办法来改变保存时间。
auto_now_add：在第一次创建对象时，Django 自动将该字段的值设置为当前时间，一般用来表示对象创建时间。它使用的同样是当前日期，而非默认值
DateTimeField 有时刻的日期字段
auto_now=False
auto_now_add=False
当auto_now或者auto_now_add设置为True时，字段会有editable=True和blank=True的设定
models.DecimalField(..., max_digits=5, decimal_places=2)
; 固定精度的十进制数的字段。
它有两个必须的参数
max_digits：数字允许的最大位数
decimal_places：小数的最大位数
例如，要存储的数字最大值是999，而带有两个小数位，你可以使用
DurationField 日期时间增量型字段，存储着python timedelta 类数据
EmailField 邮件字段    max_length
FileField 文件字段
FilePathField 文件路径字段
FloatField 小数字段
ImageField 图片字段
IntegerField 整数字段
GenericIPAddressField ip地址字段
NullBooleanField 许可null的布尔值字段
PositiveIntegerField
0 到 2147483647，支持所有数据库取值范围的安全整数。
PositiveSmallIntegerField
0 到 32767 支持所有数据库取值范围的安全短整数。
SlugField
SmallIntegerField 短整形字段
TextField 备注型字段，用于存储复杂文本
TimeField 时间字段
URLField 网址字段
UUIDField
Python UUID 数据对象，一个32位长度的ID字符串
映射字段
ForeignKeyField 一对多字段
映射字段
ManyToManyField 多对多字段
映射字段
OneToOneField 一对一字段
