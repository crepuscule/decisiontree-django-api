## api接口设计文档
### 0. 数据库设计
T:数据集合
(dataSet_id,dataSet_name,dataSet_type(0,1),table_name,size,create_time)
(数据集id,数据集名,数据集类型,所在表名称,数据量,创建时间)

T:决策树
(tree_id,dataSet_id,tree_name,tree_type,optimize_type,tree_dict,depth,nodes_num)
(树id,源训练集id,树名,树类型,优化类型,树字典,深度,结点数,创建时间)

T:分析报告
(analysis_id,tree_id,dataSet_id,analysis_name,accuracy,ifthen,content)
(报告id，源树id，测试集id，分析报告名,精度，if-then规则，其他内容)
```
建表语句:
use db_weixin;
create table dataSet(
	`dataSet_id` int not null primary key auto_increment,
	`dataSet_name` varchar(255),
	`dataSet_type` char(1) default '0',
	`table_name` varchar(255) default null,
	`size` int default null,
	`create_time` timestamp not null default current_timestamp
)

create table tree(
	`tree_id` int not null primary key auto_increment,
	`dataSet_id` int not null,
	`tree_name` varchar(255) default null,
	`tree_type` varchar(255) default null,
	`optimize_type` varchar(255) default null,
	`tree_dict` varchar(255) default null,
	`detpth` int default 0,
	`nodes_num` int default 0,
	`create_time` timestamp not null default current_timestamp
)

create table analysis(
	`analysis_id` not null primary key auto_increment,
	`tree_id` int not null,
	`dataSet_id` int not null,
    `analysis_name` varchar(255) not null,
	`accuracy` float default null,
	`ifthen` text default null,
	`content` varchar(255) default null,
	`create_time` timestamp not null default current_timestamp
)

```
### 1.使用RESTful风格接口，和微信小程序对接
Web 应用程序最重要的 REST 原则是，客户端和服务器之间的交互在请求之间是无状态的。从客户端到服务器的每个请求都必须包含理解请求所必需的信息。如果服务器在请求之间的任何时间点重启，客户端不会得到通知。此外，无状态请求可以由任何可用服务器回答，这十分适合云计算之类的环境。客户端可以缓存数据以改进性能。

在服务器端，应用程序状态和功能可以分为各种资源。资源是一个有趣的概念实体，它向客户端公开。资源的例子有：应用程序对象、数据库记录、算法等等。每个资源都使用 URI (Universal Resource Identifier) 得到一个唯一的地址。所有资源都共享统一的接口，以便在客户端和服务器之间传输状态。使用的是标准的 HTTP 方法，比如 GET、PUT、POST 和 DELETE。

下面列出了GET，DELETE，PUT和POST的典型用法:
GET 获取资源 
    安全且幂等
    获取表示
    变更时获取表示（缓存）
    200（OK） - 表示已在响应中发出
    204（无内容） - 资源有空表示
    301（Moved Permanently） - 资源的URI已被更新
    303（See Other） - 其他（如，负载均衡）
    304（not modified）- 资源未更改（缓存）
    400 （bad request）- 指代坏请求（如，参数错误）
    404 （not found）- 资源不存在
    406 （not acceptable）- 服务端不支持所需表示
    500 （internal server error）- 通用错误响应
    503 （Service Unavailable）- 服务端当前无法处理请求
POST 创建或更新资源 
    不安全且不幂等
    使用服务端管理的（自动产生）的实例号创建资源
    创建子资源
    部分更新资源
    如果没有被修改，则不过更新资源（乐观锁）
    200（OK）- 如果现有资源已被更改
    201（created）- 如果新资源被创建
    202（accepted）- 已接受处理请求但尚未完成（异步处理）
    301（Moved Permanently）- 资源的URI被更新
    303（See Other）- 其他（如，负载均衡）
    400（bad request）- 指代坏请求
    404 （not found）- 资源不存在
    406 （not acceptable）- 服务端不支持所需表示
    409 （conflict）- 通用冲突
    412 （Precondition Failed）- 前置条件失败（如执行条件更新时的冲突）
    415 （unsupported media type）- 接受到的表示不受支持
    500 （internal server error）- 通用错误响应
    503 （Service Unavailable）- 服务当前无法处理请求
PUT 创建或更新资源 
    不安全但幂等
    用客户端管理的实例号创建一个资源
    通过替换的方式更新资源
    如果未被修改，则更新资源（乐观锁）
    200 （OK）- 如果已存在资源被更改
    201 （created）- 如果新资源被创建
    301（Moved Permanently）- 资源的URI已更改
    303 （See Other）- 其他（如，负载均衡）
    400 （bad request）- 指代坏请求
    404 （not found）- 资源不存在
    406 （not acceptable）- 服务端不支持所需表示
    409 （conflict）- 通用冲突
    412 （Precondition Failed）- 前置条件失败（如执行条件更新时的冲突）
    415 （unsupported media type）- 接受到的表示不受支持
    500 （internal server error）- 通用错误响应
    503 （Service Unavailable）- 服务当前无法处理请求
DELETE 删除资源
    不安全但幂等
    删除资源
    200 （OK）- 资源已被删除
    301 （Moved Permanently）- 资源的URI已更改
    303 （See Other）- 其他，如负载均衡
    400 （bad request）- 指代坏请求
    404 （not found）- 资源不存在
    409 （conflict）- 通用冲突
    500 （internal server error）- 通用错误响应
    503 （Service Unavailable）- 服务端当前无法处理请求
    
POST和PUT在创建资源的区别在于，所创建的资源的名称(URI)是否由客户端决定。 例如为我的博文增加一个java的分类，生成的路径就是分类名/categories/java，那么就可以采用PUT方法。
统一资源接口要求使用标准的HTTP方法对资源进行操作，所以URI只应该来表示资源的名称，而不应该包括资源的操作。
通俗来说，URI不应该使用动作来描述。如POST /createUser

### 2.django rest framework的使用
1. 安装组件
```
pip install djangorestframework
pip install markdown       # Markdown support for the browsable API.
pip install django-filter  # Filtering support
```
2. 设置settings.py和url.py
```
settings.py:

INSTALLED_APPS = (
    ...
    'rest_framework',
)

url.py:
urlpatterns = [
    ...
    url('api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]
```
3. 创建相关model和Serializer(序列化器)
首先创建app，即`python manage.py startapp snippets`
在setting中注册安装snippets
在models.py中添加表
```
from django.db import models
from pygments.lexers import get_all_lexers         # 一个实现代码高亮的模块 
from pygments.styles import get_all_styles

LEXERS = [item for item in get_all_lexers() if item[1]]
LANGUAGE_CHOICES = sorted([(item[1][0], item[0]) for item in LEXERS]) # 得到所有编程语言的选项
STYLE_CHOICES = sorted((item, item) for item in get_all_styles())     # 列出所有配色风格

class Snippet(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=100, blank=True, default='')
    code = models.TextField()
    linenos = models.BooleanField(default=False)
    language = models.CharField(choices=LANGUAGE_CHOICES, default='python', max_length=100)
    style = models.CharField(choices=STYLE_CHOICES, default='friendly', max_length=100)

    class Meta:
        ordering = ('created',)
```
执行数据库同步：
```
➜  DecisionTreePredictionSystem $ python manage.py makemigrations snippets
Migrations for 'snippets':
  snippets/migrations/0001_initial.py
    - Create model Snippet

➜  DecisionTreePredictionSystem $ python manage.py migrate
Operations to perform:
  Apply all migrations: admin, auth, contenttypes, sessions, snippets, weixinapi
Running migrations:
  Applying snippets.0001_initial... OK
```

然后创建序列化类SnippetSerializer
```
from rest_framework import serializers
from snippets.models import Snippet, LANGUAGE_CHOICES, STYLE_CHOICES


class SnippetSerializer(serializers.Serializer):                # 它序列化的方式很类似于Django的forms
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(required=False, allow_blank=True, max_length=100)
    code = serializers.CharField(style={'base_template': 'textarea.html'})      # style的设置等同于Django的widget=widgets.Textarea
    linenos = serializers.BooleanField(required=False)                          # 用于对浏览器的上的显示
    language = serializers.ChoiceField(choices=LANGUAGE_CHOICES, default='python')
    style = serializers.ChoiceField(choices=STYLE_CHOICES, default='friendly')

    def create(self, validated_data):
        """
        Create and return a new `Snippet` instance, given the validated data.
        """
        return Snippet.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """
        Update and return an existing `Snippet` instance, given the validated data.
        """
        instance.title = validated_data.get('title', instance.title)
        instance.code = validated_data.get('code', instance.code)
        instance.linenos = validated_data.get('linenos', instance.linenos)
        instance.language = validated_data.get('language', instance.language)
        instance.style = validated_data.get('style', instance.style)
        instance.save()
        return instance
```

在django shell中测试序列化功能
```
➜  DecisionTreePredictionSystem $ python manage.py shell
>>> from snippets.models import Snippet
>>> from snippets.serializers import SnippetSerializer
>>> from rest_framework.renderers import JSONRenderer
>>> from rest_framework.parsers import JSONParser
>>> snippet = Snippet(code = 'foo = "bar"\n')
>>> snippet.save()
>>> snippet = Snippet(code = 'print "hello,world"')
>>> snippet.save()
>>> serializer = SnippetSerializer(snippet)
>>> serializer.data
{'id': 2, 'title': '', 'code': 'print "hello,world"', 'linenos': False, 'language': 'python', 'style': 'friendly'}
>>> print(snippet)
Snippet object (2)
```

4.在Django的视图中使用Serializer

```
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
from snippets.models import Snippet
from snippets.serializers import SnippetSerializer


@csrf_exempt
def snippet_list(request):
    """
    List all code snippets, or create a new snippet.
    """
    if request.method == 'GET':
        snippets = Snippet.objects.all()
        serializer = SnippetSerializer(snippets, many=True)
        return JsonResponse(serializer.data, safe=False)

    elif request.method == 'POST':
        data = JSONParser().parse(request)
        serializer = SnippetSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data, status=201)
        return JsonResponse(serializer.errors, status=400)
```

### 3.dataSet接口
1.直接操作dataset接口
urls匹配正则: re_path(r'^dataset/(?P<dataset_id>[0-9a-z]*)') => 对应view.dataSet(request,dataset_id)方法
接口调用说明:
    直接(网页)获取所有或者部分dataset的JSON
    method="GET":[ok]
        dataset/    =>  获取所有dataset，json数组
        dataset/x   =>  获取id为x的dataset，json
        
    通过request直接推送一个完整的datasetJSON给服务器完成构建
    method="PUT":
        dataset/    =>  解析附加的json(只能有1条，不支持批量)，插入到数据库
    通过request+dataset的id完成对某对象的删除
    
    method="DELETE":[ok]
        dataset/x   =>  删除id为x的dataset
    
    通过上传文件的方式将文件内容插入到数据库    
    method="POST":[ok]
        dataset/    =>  根据上传的csv文件，创建新的数据集表格    
                    =>  调用csv2Db模块完成根据文件名创建表格插入数据库
                    =>  需要配合uploads模块上传csv文件

*utils/csv2Db模块:
功能:创建和csv文件同名的数据表，将数据插入数据表中
输入:接收包含数据表头的csv文件的路径名和文件名
返回：返回生成数据的条数(若返回-1为创立表格失败，返回-2为插入数据失败)
异常处理:如果数据库中已经存在这个表格，自动设立表格名为xxxx_1,xxxx_2..的表格
>仍然需要的工作：
1. 后期需要开发直接调用数据库表格的脚本 / 手动生成很多已有数据集
2. 在1中，数据集合要制作两份，一份70%用于训练，另外30%用于测试（使用随机函数？？）
3. 上传时间太长的解决办法(前端假象完成/后端优化处理)


### 4.tree接口
1.直接操作tree接口
urls匹配正则: re_path(r'^tree/(?P<tree_id>[0-9a-z]*)') => 对应views.tree(request,tree_id)方法
接口调用说明:
    直接(网页)获取所有或者部分tree的JSON
    method="GET":[ok]
        tree/    =>  获取所有tree，json数组
        tree/x   =>  获取id为x的tree，json
        
    通过request直接推送一个完整的tree JSON给服务器完成构建        
    method="PUT":
        tree/    =>  解析附加的json(只能有1条，不支持批量)，插入到数据库
        
    通过request+dataset的id完成对某对象的删除        
    method="DELETE":[ok]
        tree/x   =>  删除id为x的tree
    
    通过传递一条请求构建JSON，传送需要构建tree的必要字段，服务器就能构建1棵树并存入数据库
    method="POST":(服务器端生成树)[]
        tree/    =>  解析在POST中名为tree的JSON，得出所需要训练的树的类型，数据集，在服务器端进行训练，并生成数据库记录插入数据库中
                 =>  JSON字段:tree:{"tree_name":"用于预测鸢尾花的CART决策树","tree_type":"CART","optimize_type":"null","dataSet_id":5,"fields":""}
*注意：树的detph和nodes_num需要在算法文件中得出[ok]
树深度则需要递归得出,节点数直接通过统计字符串中'name'个数

*注意：C45算法[ok]

*utils/TreeGenerator模块:[ok]
功能:根据传入的部分已知信息的DictTreePart字典，判断需要调用哪些算法来创建树并返回构建好的json树和树的其他信息
输入:从json中load出的具有部分Tree模型字段的DictTreePart字典
返回:完整的newDictTree，可以取出各字段后直接save到数据库
>仍然需要的工作：
1. 算法本身的优化，剪枝等
2. 设计出几个真的有用的预测，至少5个，将其所需要的数据进行优化（其他字段不给外界展示）
3. 随机森林！！！！


### 5.analysis接口
1.直接操作analysis接口
urls匹配正则: re_path(r'^analysis/(?P<analysis_id>[0-9a-z]*)') => 对应view.analysis(request,analysis_id)方法
接口调用说明:
    直接(网页)获取所有或者部分analysis的JSON
    method="GET":
        analysis/    =>  获取所有analysis，json数组
        analysis/x   =>  获取id为x的analysis，json

    通过request直接推送一个完整的analysis JSON给服务器完成构建           
    method="PUT":
        analysis/    =>  解析附加的json(只能有1条，不支持批量)，插入到数据库
        
    通过request+dataset的id完成对某对象的删除    
    method="DELETE":
        analysis/x   =>  删除id为x的analysis

    通过传递一条请求构建JSON，传送需要构建analysis的必要字段，服务器就能构建并存入数据库        
    method="POST":(服务器端用已有的树做分类)[]
        analysis/    =>  解析POST中名为analysis的JSON，使用JSON中指定的树进行分类
                     =>  json字段格式: analysis:{"analysis_name":"预测毕业生去向的CART决策树分析报告","dataSet_id":"16","tree_id":"18"} (analysis_id在单条预测时可无)
                     =>  其中具有两种模式：1)当json中dataSet_id中是一条观测向量时，仅返回结果{!!注意：dataSet_id中的数据不能有空格，防止空格作为新的字段}                                        
                                        3)当json中dataSet_id是1个数字，可以在数据库中取到时，则生成1个分析报告插入数据库中
*utils/AnalysisGenerator模块:[ok]
功能:根据传入的部分已知信息的DictAnalysisPart字典，判断需要调用哪些算法来对测试集进行分类处理并生成分析报告存入数据库
输入:从json中load出的具有部分Analysis模型字段的DictAnalysisPart字典
返回:完整的DictAnalysisPart，可以取出各字段后直接save到数据库




## 测试文档
### 测试步骤
1. 火狐 http://localhost:8000/weixinapi/upload上传数据集
2. 谷歌 https://apizza.net/pro/#/project/0d9f23d659bb5f9104692d10e3789ccd/dev | [POST]localhost:8000/weixinapi/tree/ | tree:{"tree_name":"","tree_type":"CART","optimize_type":"null","dataSet_id":5,"fields":"","outDataSet_id":0}(参考火狐上的字段)
3. 火狐 localhost:8000/weixinapi/tree/id && localhost:8000/weixinapi/treegraph?tree_id=查看刚刚生成的树
4. 谷歌 https://apizza.net/pro/#/project/0d9f23d659bb5f9104692d10e3789ccd/dev | [POST]localhost:8000/weixinapi/analysis/ | analysis: {"dataSet_id":"无空格的观测数据","tree_id":xx}
5. 谷歌 https://apizza.net/pro/#/project/0d9f23d659bb5f9104692d10e3789ccd/dev | [POST]localhost:8000/weixinapi/analysis/ | analysis: {"analysis_name":"分析报告","dataSet_id":18,"tree_id":21}
