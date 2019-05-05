# CART_Standard 接口文档
## 数据成员
    *数据集合(二维数组)
    dataSet = []
    *数据表头/特征名(一维数组)
    labels = []
    *数据库字段选择器
    fields = [] 
    *决策树类型(离散型Discrete/连续型Continuous)
    decisionTreeType = ""
    *数据集合
    dataSource="csv"
    *数据源名称
    sourceName=""
    *目标类型{"dictTree,json,biTree,db"}
    target="dictTree"
    *字典树
    dictTree = {}
##  构造函数
    `__init__(self,dataSource="csv",sourceName="",fields=[])`
    功能:
        生成一个CART对象后会根据数据源判断数据类型(即decisionTreeType，离散或者连续),以决定后续操作所调用的py模块
    输入:
        dataSource 指定数据源,取值 'csv','db'
        sourceName 根据dataSource而定,dataSource='csv',sourceName指文件地址;dataSource='db',sourceName指表名
        fields 当dataSource='db'时,指定用于参与测试的列，最后一列是结果列
    返回:
        无
## 生成决策树
    `GenerateCART(self,target="dictTree")`
    功能:
        根据dataSource与decisionTreeType调用相应模块完成决策树的构建，构建完成后字典树(dictTree)将存储在对象的数据成员中，后继的操作将依赖这个构造步骤
    输入:
        target 指定返回的类型，取值'dictTree','json','db'
    返回:
        dictTree/json/db
        
        
return self.decisionTreeType,self.nodes_num,self.depth
## 进行分类
    `Classify(self,observation)`
    功能:
        根据对象中已经生成好的dictTree和测试向量observation进行预测，结果返回一个字符串
    输入:
        observation,一维的测试向量，要和训练集中的数据列的顺序相同，结果列可有可无
    返回:
        预测结果,string类型
    `ClassifyAll(self,observations)`
    功能:
        根据对象中已经生成好的dictTree和测试向量集observations进行预测，结果返回一个字符串列表
    输入:
        observations,二维的测试向量集，要和训练集中的数据列的顺序相同，结果列可有可无
    返回:
        预测结果,string类型列表
## 计算精度
    `CheckAccuracy(self,dataSource='csv',sourceName="")`
    功能:
        独立地读取其他数据源计算生成决策树的精度
    输入:
        dataSource独立于对象中的其他数据源,取值'csv','db'
        sourceName独立数据源名称，可以指文件名或者表名
    输出:
        树的预测精度，float类型
        
        
## 对单个观测向量进行分类，返回预测结果
    Classify(dictTree,observation,decisionTreeType)
    输入: 从JSON中loads出来的dictTree，单条观测数据以及决策树离散/连续类型
    输出：观测结果
## 对测试集进行批量分类，返回预测结果集和精度(即一个Analysis类)
    ClassifyAndAnalysis(dictTree,dataSource,sourceName,fields,decisionTreeType)
    输入: 从JSON中loads出来的dictTree，测试集连接信息以及决策树离散/连续类型
    输出：观测结果,分析报告(需要填充 精度，ifthen，content(预测结果列表对应字符串){后期可能有增强})
## 绘图
    `DrawTree(self)`
    功能:
        根据生成的决策树调用接口显示树
