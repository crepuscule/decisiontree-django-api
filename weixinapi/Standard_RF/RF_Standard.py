'''
标准RF算法脚本

输入：
    1. 从1个第0行为特征名，其余行为数据的csv文件读入
    2. 从数据库读入
输出:
    1. 生成一个json字符串
    2. 可以打开浏览器展示图片
    3. 可以生成一条sql插入树信息到指定数据库
特性:
    1. 自动判断数据集为连续型或是离散型(连续型/离散型不允许有任何一列是离散型/连续型的)
    2. 通过调用两个RF算法模块实现上述功能
'''

import pymysql
import json


DBHOST = "47.95.196.25"
DBUSER = "root"
DBPWD = "12345678"


'''
基本功能:[ok]

需要深入理解的问题:

'''

#--------------------------数据读取--------------------------------
# I.1 从一个有表头的csv文件读取数据判断是否为离散型
def identifyType_csv(filename='data'):
    f = open(filename+".csv")
    line = f.readline()
    line = f.readline()
    newline = line.strip('\n').split(',')
    #连续型的最后一列可能是字符串，应该去除
    line = newline[:-1]
    for value in line:
        #print(value,"\nis?",is_number(value))
        if is_number(value):
            pass
        else:
            return "Discrete"
    return "Continuous"

def identifyType_db(dbname="db_slg",tablename='lenses_one',fields=[]):
    print("``````````RF_Standard.py```````````````````\nin identifyType_db() , use %s . %s " % (dbname,tablename), "\nfields:\n" ,fields)
    db=pymysql.connect(DBHOST,DBUSER,DBPWD,dbname,charset="utf8")
    cur = db.cursor()
    if fields == []:
        #如果fields为空，则直接取出数据库中所有不是id的字段
        querySql = "select COLUMN_NAME from information_schema.COLUMNS where table_name = '%s' and COLUMN_NAME not like '%%id' " % (tablename)        
        cur.execute(querySql)
        for value in cur.fetchall():
            fields.append(value[0])  
        print("\n!fixed fields:\n" , fields)
        
    sql = "select "
    for value in fields:
        sql+="`%s`," % (value)
    sql = sql[:-1]
    sql += "from %s where `%s` != '-' limit 5" % (tablename,fields[-1])
    cur.execute(sql)
    #数据库读取返回的是元组，这里转化为list注意最有一列结果列不需要测试
    tmpdata = cur.fetchall()
    if len(tmpdata) < 5:
        return {"message":"can not build Tree,Data volume is too small"}
    
    tmpdata = list(tmpdata[0][:-1])
    for value in tmpdata:
        #print(value,":",type(value)," is Number?",is_number(value))
        if value == '-' or is_number(value):
            pass
        else:
            return "Discrete"
    return "Continuous"


#----------------------工具函数--------------------------
def is_number(s):
    try:
        complex(s) # for int, long, float and complex
    except ValueError:
        return False
    return True
    

#----------------------总控函数--------------------------
class RF:
    '''常用变量定义'''
    #数据集合(二维数组)
    dataSet = []
    #数据表头/特征名(一维数组)
    labels = []
    #数据库字段选择器
    fields = []
    #决策树类型(离散型Discrete/连续型Continuous)
    decisionTreeType = ""
    #数据集合
    dataSource="csv"
    #数据源名称
    sourceName=""
    #目标类型{"randomForest,json,biTree,db"}
    target="dictTree"
    #字典树
    dictTree = {}
    #树的相关属性
    depth = 0
    nodes_num = 0
    datasize = 0
    costtime = 0.0
    trainACC = 0.0
    randomForest = []
    
    #--------------------------------构造--------------------------------------------
    def __init__(self,dataSource="csv",sourceName="db_slg.lenses_one",fields=[]):
        #数据集合
        self.dataSource=dataSource
        #数据源名称
        self.sourceName=sourceName
        self.fields = fields
        '''读取数据判断类型'''
        if dataSource == 'csv':
            self.decisionTreeType = identifyType_csv(sourceName)
        elif dataSource == "db":
            dbname = sourceName.split('.')[0]
            tablename = sourceName.split('.')[1]
            self.decisionTreeType = identifyType_db(dbname,tablename,fields)
        else:
            return {"message":"please specify the dataSource, csv or db" }

    def GenerateRF(self,trees_num, max_depth, sample_ratio, feature_ratio,target):
        '''调用模块,构造随机森林，该森林一定是dictTree型，方便进行预测'''
        if self.decisionTreeType == "Discrete":
            from weixinapi.Standard_RF import RF_Discrete          
            myRF = RF_Discrete.RandomForest(trees_num, max_depth, 1, sample_ratio, feature_ratio)
            myRF.loadDataSet('db','in',self.fields,self.sourceName)
            self.randomForest = myRF.build_RandomForest("dictTree")
            self.properties = myRF.getProperties()
        elif self.decisionTreeType == "Continuous":
            from weixinapi.Standard_RF import RF_Continuous          
            myRF = RF_Continuous.RandomForest(trees_num, max_depth, 1, sample_ratio, feature_ratio)
            myRF.loadDataSet('db','in',self.fields,self.sourceName)
            self.randomForest = myRF.build_RandomForest("dictTree")
            self.properties = myRF.getProperties()
        else:
            print('Generate RF Error!')
            self.randomForest = [{'message':'Generate RF Error! type not specify or dataset has a problem','children':"null"}]
        
        #如果指定返回dictTree
        if target == "dictTree":
            return self.randomForest
        #默认就返回json
        else:
            return json.dumps(self.randomForest)
    
    
    #--------------------------------属性与分类--------------------------------------------
    def GetProperties(self):
        return self.properties
    
    '''
    def Classify(self,observation):
        if self.decisionTreeType == "Discrete":
            resultDict = RF_Discrete.Classify(self.randomForest,observation)
        elif self.decisionTreeType == "Continuous":
            resultDict = RF_Continuous.Classify(self.randomForest,observation) 
        else:
            print('"please specify the type, Discrete or Continuous"')
            resultDict = {}
        print(observation , " => ",resultDict)
        return resultDict                
    '''
    #def ClassifyAll(self,observations):
        #if self.decisionTreeType == "Discrete":
            #import RF_Discrete            
            #resultDict = RF_Discrete.ClassifyAll(self.randomForest,observations) 
        #elif self.decisionTreeType == "Continuous":
            #resultDict = RF_Continuous.ClassifyAll(self.randomForest,observations) 
        #else:
            #print('"please specify the type, Discrete or Continuous"')
            #resultDict = {}
        #print(observations , " => ",resultDict)
        #return resultDict
    
    
    @staticmethod
    #该静态方法直接传入树,观测变量,决策树数据类型即可进行分类，不需要labels
    def Classify(randomForest,observation,decisionTreeType):
        if decisionTreeType == "Discrete":
            from weixinapi.Standard_RF import RF_Discrete 
            resultDict = RF_Discrete.RandomForest.bagging_predict(randomForest,observation)
        elif decisionTreeType == "Continuous":
            from weixinapi.Standard_RF import RF_Continuous 
            resultDict = RF_Continuous.RandomForest.bagging_predict(randomForest,observation) 
        else:
            print('"please specify the type, Discrete or Continuous"')
            resultDict = {}
        #print(observation , " => ",resultDict)
        return resultDict
    
     
    @staticmethod
    #该静态方法直接传入树,测试集相关约束,决策树数据类型即可进行分类和分析，不需要labels
    def ClassifyAndAnalysis(randomForest,dataSource,sourceName,fields,decisionTreeType):
        if decisionTreeType == "Discrete":
            from weixinapi.Standard_RF import RF_Discrete            
            accuracy,classes = RF_Discrete.RandomForest.accuracy_metric(randomForest,dataSource,sourceName,fields)
        elif decisionTreeType == "Continuous":
            from weixinapi.Standard_RF import RF_Continuous             
            accuracy,classes = RF_Continuous.RandomForest.accuracy_metric(randomForest,dataSource,sourceName,fields)
        else:
            accuracy = 0.0
            classes = []
            return {"message":"please specify the dataSource, csv or db" }            
        print ('accuracy:{:.2%}'.format(accuracy))
        return accuracy,classes
    
    def DrawTree(self):
        import os,json
        cmd = "firefox 'http://api.crepuscule.xyz/weixinapi/drawtree?json="
        cmd += json.dumps(self.dictTree)
        cmd += "'"
        #print(cmd)
        os.system(cmd)
        
#----------------------模块直接执行--------------------------
if __name__ == '__main__':
 
    fields=['English','CET4','CET6','AdvancedMath','LinearAlgebra','ProbabilityTheory','DataStructure','DataBase','OperatingSystem','CppProgramming','ProgrammingPractice','JavaProgramming','COM_VC2']
    
    control = RF('db',"db_dataset.15级计算机专业个人成绩离散化表_train",fields)
    randomForest = control.GenerateRF(500, 30, 0.3, 0.4,'dictTree')
    print(control.GetProperties())
    testACC = control.ClassifyAndAnalysis(randomForest,'db','db_dataset.15级计算机专业个人成绩离散化表_test',fields,"Discrete")
    print("测试精度:",testACC)

