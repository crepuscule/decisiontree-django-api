'''CART_Continuous.py'''
import re
import json
import pymysql

DBHOST = "47.95.196.25"
DBUSER = "root"
DBPWD = "12345678"

'''
基本功能:[]
1. 缺少剪枝功能

需要深入理解的问题:
1. 创建树的流程
2. 更加深入的决策树的评定方法(单纯的精度太单薄)
'''


#------------------------I.数据读取----------------------------
def readFromCSV(filename='data'):
    f = open(filename+".csv")
    datas = []
    # 开始读取数据集
    for line in f:
        newline = line.strip('\n').split(',')
        # 插入到datas
        datas.append(newline)        
    f.close()
    #print(datas)
    labels = datas[0][:len(datas[1])-1] #这里根据第2行的数据列数来决定labels裁剪多少，labels列数总比dataset列数少1
    dataSet = datas[1:] #第二行开始就是数据集了
    return dataSet,labels

def readFromDB(dbname="db_dataset",tablename='iris',fields=[]):
    print("``````````````````````CART_Continuous.py``````````````````````````\nin readFromDB() , use %s . %s " % (dbname,tablename), "\nfields:\n" ,fields)
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
    sql += "from %s where `%s` != '-' " % (tablename,fields[-1])
    cur.execute(sql)
    
    #tmpdata = list(cur.fetchall())
    dataSet = []
    #数据库读取返回的是元组，这里通过循环将二维元组化为list
    for line in list(cur.fetchall()):
        dataSet.append(list(line))
    for i  in range(len(dataSet)):
        #最后一列不需要数据清洗，一定有值，只是需要离散话映射
        for j in range(len(dataSet[i])-1):
            if dataSet[i][j] == '-':
                dataSet[i][j] = 0.0
            #离散型的，需要全部转化为浮点型
            dataSet[i][j] = float(dataSet[i][j])
        #如果最后一列是数字，则需要离散化(一般只是对于等级考试预测数据集合)
        if is_number(dataSet[i][-1]):
            dataSet[i][-1] = resultDiscretization(dataSet[i][-1])
    #这里根据dataset数据列数来决定labels裁剪，总比dataset列数少1

    labels = fields[:len(dataSet[0])-1]
    print("\n------------------------------SQL:------------------------------\n",sql,
          "\n--------------------------前10条dataSet:---------------------\n",dataSet[:10],
          "\n-----------------------------Labels:----------------------------\n",labels)
    return dataSet,labels


def is_number(s):
    try:
        complex(s) # for int, long, float and complex
    except ValueError:
        return False
    return True


def resultDiscretization(origin):
    origin = float(origin)
    #上无上限，下无下限
    if origin >= 90:
      return "excellent"
    elif origin >= 80 and origin <= 89:
      return "good"
    elif origin >= 60 and origin <= 79:
      return "pass"
    else:
      return "failed"
  
  
#-------------------------II. 决策树生成核心算法------------------------
#II.1 基尼指数计算
def calGini(dataSet):
    numEntries = len(dataSet)
    labelCounts={}
    for featVec in dataSet: 
        currentLabel = featVec[-1]
        if currentLabel not in labelCounts.keys(): labelCounts[currentLabel] = 0
        labelCounts[currentLabel] += 1
    gini=1
    for label in labelCounts.keys():
        prop=float(labelCounts[label])/numEntries
        gini -=prop*prop
    return gini

#II.2 分割数据集合
def splitDataSet(dataSet, axis, value,threshold):
    retDataSet = []
    if threshold == 'lt':
        for featVec in dataSet:
            if featVec[axis] <= value:
                retDataSet.append(featVec)
    else:
        for featVec in dataSet:
            if featVec[axis] > value:
                retDataSet.append(featVec)

    return retDataSet

#II.3 返回最多的类别名
def majorityCnt(classList):
    classCount={}
    for vote in classList:
        if vote not in classCount.keys(): classCount[vote] = 0
        classCount[vote] += 1
    sortedClassCount = sorted(classCount.iteritems(), key=operator.itemgetter(1), reverse=True)
    return sortedClassCount[0][0]
    #return max(classCount)

#II.4 选取最佳分割点
def chooseBestFeatureToSplit(dataSet):
    numFeatures = len(dataSet[0]) - 1
    bestGiniGain = 1.0; bestFeature = -1;bsetValue=""
    for i in range(numFeatures):        #遍历特征
        featList = [example[i] for example in dataSet]#得到特征列
        uniqueVals = list(set(featList))       #从特征列获取该特征的特征值的set集合
        uniqueVals.sort()
        for value in uniqueVals:# 遍历所有的特征值
            GiniGain = 0.0
            # 左增益
            left_subDataSet = splitDataSet(dataSet, i, value,'lt')
            left_prob = len(left_subDataSet)/float(len(dataSet))
            GiniGain += left_prob * calGini(left_subDataSet)
            # print left_prob,calGini(left_subDataSet),
            # 右增益
            right_subDataSet = splitDataSet(dataSet, i, value,'gt')
            right_prob = len(right_subDataSet)/float(len(dataSet))
            GiniGain += right_prob * calGini(right_subDataSet)
            # print right_prob,calGini(right_subDataSet),
            # print GiniGain
            if (GiniGain < bestGiniGain):       #比较是否是最好的结果
                bestGiniGain = GiniGain         #记录最好的结果和最好的特征
                bestFeature = i
                bsetValue=value
    return bestFeature,bsetValue

#II.5 创建树
def createTree(dataSet,labels,text):
    classList = [example[-1] for example in dataSet]
    # print dataSet
    if classList.count(classList[0]) == len(classList):
        return {"name":classList[0],"col":"null","text":text,"children":"null"}#所有的类别都一样，就不用再划分了
    if len(dataSet) == 1: #如果没有继续可以划分的特征，就多数表决决定分支的类别
        return {"name":majorityCnt(classList),"col":"null","text":text,"children":"null"}
    bestFeat,bsetValue = chooseBestFeatureToSplit(dataSet)
    # print bestFeat,bsetValue,labels
    bestFeatLabel = labels[bestFeat]
    if bestFeat==-1:
        return majorityCnt(classList)
    myTree = {"name":bestFeatLabel,"col":bestFeat,"text":text,"children":[{},{}]}
    featValues = [example[bestFeat] for example in dataSet]
    uniqueVals = list(set(featValues))
    subLabels = labels[:]
    # print bsetValue
    #myTree[bestFeatLabel][bestFeatLabel+'<='+str(round(float(bsetValue),3))] = createTree(splitDataSet(dataSet, bestFeat, bsetValue,'lt'),subLabels)
    myTree["children"][1] = createTree(splitDataSet(dataSet,bestFeat,bsetValue,'lt'),subLabels,'<='+str(round(float(bsetValue),3)))
    #myTree[bestFeatLabel][bestFeatLabel+'>'+str(round(float(bsetValue),3))] = createTree(splitDataSet(dataSet, bestFeat, bsetValue,'gt'),subLabels)
    myTree["children"][0] = createTree(splitDataSet(dataSet, bestFeat, bsetValue,'gt'),subLabels,'>'+str(round(float(bsetValue),3)))
    return myTree

#---------------------------------III.分类评价----------------------------------
#连续型分类不同于离散型
def classify(jsonTree,observation):
    #如果是叶子节点
    if jsonTree["children"]=="null":
        return jsonTree["name"]
    #是分支节点
    else:
        #找到本节点属性列对应的属性值
        v=float(observation[jsonTree['col']])#nameToIndex(jsonTree['name'],labels)]
        branch=None
        #如果这个值符合节点的子节点的分支上的引导文字中指定的数字范围
        threshold = re.findall(r"\d+\.?\d*",jsonTree["children"][0]["text"])[0]
        if v > float(threshold):
            branch=jsonTree["children"][0]
        else:
            branch=jsonTree["children"][1]
        return classify(branch,observation)



def checkAccuracy(jsonTree,observations):    
    total = float(len(observations))
    if total <= 0:
        return 0
    correct = 0.0
    classes = []
    #仅用于输出
    counts = 0
    for observation in observations:
        result = classify(jsonTree,observation)
        classes.append(result)
        if str(result) == str(observation[-1]):
            correct += 1.0
        #仅用于输出
        if counts < 10:
            print("line:",observation[:-1])
            print("result: 真实:",observation[-1],"|预测:",result)
            counts += 1
    return correct/total,classes


#-------------------------X.总控制函数()------------------------------
#生成树，预测单条，预测多条，计算精度
#--------------------------------------------------------------------
#生成CART树
#输入:dataSource:{csv,db} sourceName:{csv,db.table} fields{}   target:{tree,json}
#输出:根据target输出tree,json
def GenerateCART(dataSource="csv",sourceName="db_dataset.iris",fields=[],target="dictTree"):
    '''常用变量定义'''
    #数据集合(二维数组)
    dataSet = []
    #数据表头/特征名(一维数组)
    labels = []
    #字典树
    dictTree = {}
 
    '''数据源读取'''
    if dataSource == 'csv':
        dataSet,labels = readFromCSV(sourceName)
    elif dataSource == "db":
        dbname = sourceName.split('.')[0]
        tablename = sourceName.split('.')[1]
        dataSet,labels = readFromDB(dbname,tablename,fields)
    else:
        return {"message":"please specify the dataSource, csv or db" }

    '''树训练'''
    dictTree = createTree(dataSet,labels,"null")
    
    '''树剪枝/优化'''
    #prune(cartTree,0.3)
    
    '''树输出'''
    if target == "dictTree":
        print('-------------------------dictTree:----------------------------\n',json.dumps(dictTree))
        return dictTree
    elif target == "db":
        pass
    elif target == "json":
        print('-------------------------json:----------------------------\n',json.dumps(dictTree)) 
        return (json.dumps(dictTree))
    else:
        return {"message":"please specify the target, dictTree，biTree or json"}

# 对新的观测数据进行分类。observation为观测数据。dictTree为训练好的字典树
def Classify(dictTree,observation):
    return classify(dictTree,observation)

# 对新的观测数据集进行批量分类。observations为观测数据集。dictTree为训练好的字典树
def ClassifyAll(dictTree,observations):
    classes = []
    for observation in observations:
        classes.append(classify(dictTree,observation))
    return classes


#测试精度(dictTree字典树,测试向量集(二维数组))
##返回精度和预测结果集合
def CheckAccuracy(dictTree,dataSource='',sourceName="",fields=[]):   
    '''数据源读取'''
    if dataSource == 'csv':
        dataSet,labels = readFromCSV(sourceName)
    elif dataSource == "db":
        dbname = sourceName.split('.')[0]
        tablename = sourceName.split('.')[1]
        dataSet,labels = readFromDB(dbname,tablename,fields)          
    elif dataSource == "list":
        dataSet = sourceName
    else:
        return {"message":"please specify the dataSource, csv or db" }
    
    print('----------------CheckAccuracy DataSet(top10):-------------------\n',dataSet[:10],'\n')
    return checkAccuracy(dictTree,dataSet)    


#----------------------模块直接执行--------------------------
if __name__ == '__main__':
    #生成CART (数据源类型，数据源，参与生成的域名)
    #dictTree = GenerateCART("db","db_dataset.personal_transcripts_cs",['CET4','AdvancedMath','LinearAlgebra','ProbabilityTheory','DataStructure','DataBase','ComputerNetwork','OperatingSystem','CompositionPrinciple','CppProgramming','ProgrammingPractice','JavaProgramming','CSorSE','NCRE_CPP2'],"dictTree")
    
    dictTree = GenerateCART("db","db_dataset.iris",[],"dictTree")
    #进行单条预测(决策树，观测数据)
    print("--结果-->",Classify(dictTree,[ 443.0,  94.0, 96.0, 90.0, 95.0, 92.0, 0.0, 95.0, 0.0, 90.0, 95.0, 89.0, 0.0]))#结果:'pass'
    #print("--结果-->",Classify(dictTree,[ 479.0,  69.5, 67.0, 66.0, 52.3, 78.0, 0.0, 75.0, 0.0, 43.5, 0.0, 87.0, 0.0]))#结果:'failed'
    
    
    #进行多条预测检测精度(决策树,观测数据集合)
    #accuracy = CheckAccuracy(dictTree,'db','db_dataset.personal_transcripts_cs',['CET4','AdvancedMath','LinearAlgebra','ProbabilityTheory','DataStructure','DataBase','ComputerNetwork','OperatingSystem','CompositionPrinciple','CppProgramming','ProgrammingPractice','JavaProgramming','CSorSE','NCRE_CPP2'])
    #print('accuracy: {:.2%}'.format(accuracy))

    #print('accuracy: {:.2%}'.format(CheckAccuracy(dictTree,'db','db_dataset.iris',[])))
