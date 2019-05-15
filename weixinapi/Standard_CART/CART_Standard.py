'''
标准CART算法脚本

输入：
    1. 从1个第0行为特征名，其余行为数据的csv文件读入
    2. 从数据库读入
输出:
    1. 生成一个json字符串
    2. 可以打开浏览器展示图片
    3. 可以生成一条sql插入树信息到指定数据库
特性:
    1. 自动判断数据集为连续型或是离散型(连续型/离散型不允许有任何一列是离散型/连续型的)
    2. 通过调用两个CART算法模块实现上述功能
'''



from weixinapi.Standard_CART import CART_Discrete
from weixinapi.Standard_CART import CART_Continuous
#import CART_Discrete
#import CART_Continuous
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
    print("``````````CART_Standard.py```````````````````\nin identifyType_db() , use %s . %s " % (dbname,tablename), "\nfields:\n" ,fields)
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

def getTreeDepth(jsonTree):
    #如果不是叶子节点
    if jsonTree["children"] != "null":        
        depths = [0]*len(jsonTree["children"])
        for i in range(len(depths)):
            depths[i] = getTreeDepth(jsonTree["children"][i])
        maxDepth = 0
        for i in range(len(depths)):
            if depths[i] > maxDepth:
                maxDepth = depths[i]
        return maxDepth+1
    else:
        return 0
    

#----------------------总控函数--------------------------
class CART:
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
    #目标类型{"dictTree,json,biTree,db"}
    target="dictTree"
    #字典树
    dictTree = {}
    #树的相关属性
    depth = 0
    nodes_num = 0
    datasize = 0
    costtime = 0.0
    trainACC = 0.0

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

    def GenerateCART(self,target="dictTree",pruning="none",outSourceName="db_slg.iri_test"):
        '''调用模块'''
        if self.decisionTreeType == "Discrete":
            #生成离散特有中间树：cartTree
            self.dictTree,self.datasize,self.costtime,self.trainACC = CART_Discrete.GenerateCART(self.dataSource,self.sourceName,self.fields,"dictTree",pruning,outSourceName)
        elif self.decisionTreeType == "Continuous":
            self.dictTree,self.datasize,self.costtime,self.trainACC = CART_Continuous.GenerateCART(self.dataSource,self.sourceName,self.fields,"dictTree",pruning,outSourceName)
        else:
            print('Generate CART Error!')
            self.dictTree = {'message':'Generate CART Error! type not specify or dataset has a problem','children':"null"}
        
        #如果指定返回dictTree
        if target == "dictTree":
            return self.dictTree
        #默认就返回json
        else:
            return json.dumps(self.dictTree)

    def CalcProperties(self):
        #树深度则需要递归得出
        self.depth = getTreeDepth(self.dictTree) + 1
        #节点数直接通过统计字符串中'name'个数
        jsonTree = json.dumps(self.dictTree)
        self.nodes_num = jsonTree.count('"name"')
        return self.decisionTreeType,self.nodes_num,self.depth,self.datasize,self.costtime,self.trainACC
    
    '''
    def Classify(self,observation):
        if self.decisionTreeType == "Discrete":
            resultDict = CART_Discrete.Classify(self.dictTree,observation)
        elif self.decisionTreeType == "Continuous":
            resultDict = CART_Continuous.Classify(self.dictTree,observation) 
        else:
            print('"please specify the type, Discrete or Continuous"')
            resultDict = {}
        print(observation , " => ",resultDict)
        return resultDict                
    '''
    def ClassifyAll(self,observations):
        if self.decisionTreeType == "Discrete":
            resultDict = CART_Discrete.ClassifyAll(self.dictTree,observations) 
        elif self.decisionTreeType == "Continuous":
            resultDict = CART_Continuous.ClassifyAll(self.dictTree,observations) 
        else:
            print('"please specify the type, Discrete or Continuous"')
            resultDict = {}
        print(observations , " => ",resultDict)
        return resultDict
    
    @staticmethod
    #该静态方法直接传递字典树即可生成ifthen规则
    def GenerateIfThen(dictTree,decisionTreeType):
        stack=[]
        rules = set()
    
        def toifthen_con(jsonTree):
            #如果是孩子节点，到底了，应该加then
            if jsonTree["children"] == "null":
                stack.append(' THEN ' + jsonTree["name"])
                rules.add(''.join(stack))
                stack.pop()
            else:
                ifnd = 'IF ' if not stack else ' AND '
                stack.append(ifnd + jsonTree['name'] + ' ')
                for i in range(len(jsonTree['children'])):
                    stack.append(jsonTree['children'][i]['text'])
                    toifthen_con(jsonTree['children'][i])
                    stack.pop()
                stack.pop()
    
        def toifthen_dis(jsonTree):
            #如果是孩子节点，到底了，应该加then
            if jsonTree["children"] == "null":
                stack.append(' THEN ' + jsonTree["name"])
                rules.add(''.join(stack))
                stack.pop()
            else:
                ifnd = 'IF ' if not stack else ' AND '
                stack.append(ifnd + jsonTree['name'] + ' EQUALS ')
                for i in range(len(jsonTree['children'])):
                    stack.append(jsonTree['children'][i]['text'])
                    toifthen_dis(jsonTree['children'][i])
                    stack.pop()
                stack.pop()
        if decisionTreeType == "Discrete":
            toifthen_dis(dictTree)
        elif decisionTreeType == "Continuous":
            toifthen_con(dictTree)
        else:
            rules.add('ifthen Generator comes across an error')
        ruleList = list(rules)
        return "\n".join(ruleList)
    
    @staticmethod
    #该静态方法直接传入树,观测变量,决策树数据类型即可进行分类，不需要labels
    def Classify(dictTree,observation,decisionTreeType):
        if decisionTreeType == "Discrete":
            resultDict = CART_Discrete.Classify(dictTree,observation)
        elif decisionTreeType == "Continuous":
            resultDict = CART_Continuous.Classify(dictTree,observation) 
        else:
            print('"please specify the type, Discrete or Continuous"')
            resultDict = {}
        #print(observation , " => ",resultDict)
        return resultDict
    
     
    @staticmethod
    #该静态方法直接传入树,测试集相关约束,决策树数据类型即可进行分类和分析，不需要labels
    def ClassifyAndAnalysis(dictTree,dataSource='db',sourceName="db_slg.lenses_one",fields=[],decisionTreeType="Discrete"):
        if decisionTreeType == "Discrete":
            accuracy,classes = CART_Discrete.CheckAccuracy(dictTree,dataSource,sourceName,fields)
        elif decisionTreeType == "Continuous":
            accuracy,classes = CART_Continuous.CheckAccuracy(dictTree,dataSource,sourceName,fields)
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
    #生成CART (数据源类型，数据源，参与生成的域名)
    #control = CART('db','db_slg.personal_transcripts_cs',fields=['English','CET4','CET6','AdvancedMath','LinearAlgebra','ProbabilityTheory','DataStructure','DataBase','ComputerNetwork','OperatingSystem','CompositionPrinciple','CppProgramming','ProgrammingPractice','JavaProgramming','CSorSE','NCRE_CPP2'])#,'NCRE_NET3'])
    #control.GenerateCART('json')
    
    #进行单条预测(决策树，观测数据)
    #print("--结果-->",Classify(['failed', 'pass', 'failed', 'excellent', 'excellent', 'excellent', 'excellent', 'excellent', 'failed', 'excellent', 'failed', 'excellent', 'excellent', 'good', 'failed']))
    
    #进行多条预测检测精度(决策树,观测数据集合)
    #accuracy = control.CheckAccuracy('db','db_slg.personal_transcripts_cs',['English','CET4','CET6','AdvancedMath','LinearAlgebra','ProbabilityTheory','DataStructure','DataBase','ComputerNetwork','OperatingSystem','CompositionPrinciple','CppProgramming','ProgrammingPractice','JavaProgramming','CSorSE','NCRE_CPP2'])

    '''
    control = CART('db','db_slg.personal_transcripts_discrete_cs',fields=['English','CET4','CET6','AdvancedMath','LinearAlgebra','ProbabilityTheory','DataStructure','DataBase','ComputerNetwork','OperatingSystem','CompositionPrinciple','CppProgramming','ProgrammingPractice','JavaProgramming','CSorSE','NCRE_CPP2'])
    
    control.GenerateCART('json')
    print("--结果-->",control.Classify(['failed', 'pass', 'failed', 'excellent', 'excellent', 'excellent', 'excellent', 'excellent', 'failed', 'excellent', 'failed', 'excellent', 'excellent', 'good', 'failed']))
    
    accuracy = control.CheckAccuracy('db','db_slg.personal_transcripts_discrete_cs',['English','CET4','CET6','AdvancedMath','LinearAlgebra','ProbabilityTheory','DataStructure','DataBase','ComputerNetwork','OperatingSystem','CompositionPrinciple','CppProgramming','ProgrammingPractice','JavaProgramming','CSorSE','NCRE_CPP2'])        
    
    print(control.CalcProperties())
    control.DrawTree()
    '''
    fields=['English','CET4','CET6','AdvancedMath','LinearAlgebra','ProbabilityTheory','DataStructure','DataBase','OperatingSystem','CppProgramming','ProgrammingPractice','JavaProgramming','COM_VC2']
    
    #fields = []
    
    control = CART('db',"db_dataset.15级计算机专业个人成绩表_train",fields)
    dictTree = control.GenerateCART('dictTree','inpruning','db_dataset.15级计算机专业个人成绩表_test')
    print(json.dumps(dictTree))
    print(control.CalcProperties())
    testACC = control.ClassifyAndAnalysis(dictTree,'db','db_dataset.15级计算机专业个人成绩表_test',fields,"Continuous")
    print("测试精度:",testACC[0])
    
    print(control.GenerateIfThen(dictTree,(control.CalcProperties())[0]))
    print(json.dumps(dictTree))
