'''CART_Continuous.py'''
import re
import json
import pymysql
import operator
import copy
import datetime

DBHOST = "47.95.196.25"
DBUSER = "root"
DBPWD = "12345678"

#内部交叉验证测试集比例
SPLIT_PROP = 0.25
#评价模型测试正确率所占比
TESTACC_PROP = 0.6
#剪枝时剪枝后误差比重（值越大剪枝数越少）
WEIGHT = 1.675

'''
基本功能:[ok]

需要深入理解的问题:
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

def readFromDB(dbname="db_slg",tablename='iris',fields=[]):
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
    return max(classCount, key=classCount.get)

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
            # 右增益
            right_subDataSet = splitDataSet(dataSet, i, value,'gt')
            right_prob = len(right_subDataSet)/float(len(dataSet))
            GiniGain += right_prob * calGini(right_subDataSet)
            if (GiniGain < bestGiniGain):       #比较是否是最好的结果
                bestGiniGain = GiniGain         #记录最好的结果和最好的特征
                bestFeature = i
                bsetValue=value
    return bestFeature,bsetValue

#II.5 创建树
def createTree(dataSet,labels,text,pruning="nopruning",test_data=[]):
    classList = [example[-1] for example in dataSet]
    if classList.count(classList[0]) == len(classList):
        return {"name":classList[0],"col":"null","text":text,"children":"null"}#所有的类别都一样，就不用再划分了
    if len(dataSet) == 1: #如果没有继续可以划分的特征，就多数表决决定分支的类别
        return {"name":majorityCnt(classList),"col":"null","text":text,"children":"null"}
    bestFeat,bsetValue = chooseBestFeatureToSplit(dataSet)
    #剪枝需要的
    #labels_copy = labels[:]
    # print bestFeat,bsetValue,labels
    bestFeatLabel = labels[bestFeat]
    if bestFeat==-1:
        return {"name":majorityCnt(classList),"col":"null","text":text,"children":"null"}
    myTree = {"name":bestFeatLabel,"col":bestFeat,"text":text,"children":[{},{}]}
    featValues = [example[bestFeat] for example in dataSet]
    uniqueVals = list(set(featValues))
    subLabels = labels[:]
    # print bsetValue
    #myTree[bestFeatLabel][bestFeatLabel+'<='+str(round(float(bsetValue),3))] = createTree(splitDataSet(dataSet, bestFeat, bsetValue,'lt'),subLabels)
    myTree["children"][1] = createTree(splitDataSet(dataSet,bestFeat,bsetValue,'lt'),subLabels,'<='+str(round(float(bsetValue))))
    #myTree[bestFeatLabel][bestFeatLabel+'>'+str(round(float(bsetValue),3))] = createTree(splitDataSet(dataSet, bestFeat, bsetValue,'gt'),subLabels)
    myTree["children"][0] = createTree(splitDataSet(dataSet, bestFeat, bsetValue,'gt'),subLabels,'>'+str(round(float(bsetValue))))
    '''
    #后剪枝算法的实现
    if pruning == "pruning":
        #由于默认是空的，所以以防万一
        if test_data == []:
            test_data = dataSet
        if calcTestErr(myTree, test_data, labels_copy) > testMajor(majorityCnt(classList), test_data):
            return majorityCnt(classList)
    '''
    return myTree

#---------------------------------III.分类评价----------------------------------
#连续型分类不同于离散型
def classify(jsonTree,observation,labels):
    #如果是叶子节点
    if jsonTree["children"]=="null":
        return jsonTree["name"]
    #是分支节点
    else:
        #找到本节点属性列对应的属性值
        #v=float(observation[jsonTree['col']])
        #v = float(observation[nameToIndex(jsonTree['name'],labels)])
        v = float(observation[labels.index(jsonTree['name'])])
        branch=None
        #如果这个值符合节点的子节点的分支上的引导文字中指定的数字范围
        threshold = re.findall(r"\d+\.?\d*",jsonTree["children"][0]["text"])[0]
        if v > float(threshold):
            branch=jsonTree["children"][0]
        else:
            branch=jsonTree["children"][1]
        return classify(branch,observation,labels)

def checkAccuracy(jsonTree,observations,labels):    
    total = float(len(observations))
    if total <= 0:
        return 0
    correct = 0.0
    classes = []
    #仅用于输出
    counts = 0
    for observation in observations:
        result = classify(jsonTree,observation,labels)
        classes.append(result)
        if str(result) == str(observation[-1]):
            correct += 1.0
        #仅用于输出
        if counts < 10:
            #print("line:",observation[:-1])
            #print("result: 真实:",observation[-1],"|预测:",result)
            counts += 1
    return correct/total,classes


#-------------------------IV.剪枝-----------------------------------
#划分交叉验证数据集合
def createCVDataSet(dataSet,some_list=[0,1],probabilities=[1-SPLIT_PROP,SPLIT_PROP]):
    import random 
    import time
    random.seed(time.time())
    
    def random_pick(some_list=[0,1],probabilities=[1-SPLIT_PROP,SPLIT_PROP]): 
        x = random.uniform(0,1) 
        cumulative_probability = 0.0 
        for item,item_probability in zip(some_list, probabilities): 
            cumulative_probability += item_probability 
            if x < cumulative_probability:
                break 
        return item 
    
    list0 = []
    list1 = []
    testRaito = 0
    while(testRaito < probabilities[1]-0.05 or testRaito > probabilities[1]+0.05):
        list0 = []
        list1 = []
        for line in dataSet:
            #如果返回1,说明将数据写到测试集合
            if random_pick():
                list1.append(line)
            #否则写到训练集合
            else:
                list0.append(line)

        testRaito = float(len(list1))/(len(list1)+len(list0))
        print("训练集合占比",testRaito)
    return list0,list1

# 计算预测误差 
def calcTestErr(myTree,testData,labels):
    errorCount = 0.0
    for i in range(len(testData)): 
        if classify(myTree,testData[i],labels) != testData[i][-1]:
            errorCount += 1 
    return float(errorCount)
    
# 计算剪枝后的预测误差
def testMajor(major,testData):  
    errorCount = 0.0  
    for i in range(len(testData)):  
        if major != testData[i][-1]:  
            errorCount += 1   
    return float(errorCount)

#weight剪枝权重，值越大剪去的枝越少
def pruningTree(inputTree,dataSet,testData,labels,weight=WEIGHT):#weight=1.675):    
    #当前节点的属性名称
    firstStr = inputTree['name']    #firstStr = list(inputTree.keys())[0]       #所有keys中的第一个
    #当前节点的所有孩子
    children = inputTree["children"]  #children = inputTree[firstStr]        # 获取子树
    #当前数据中所有类别
    classList = [example[-1] for example in dataSet]  #    classList = [example[-1] for example in dataSet]   #这个数据的类别列表
    
    #如果是分支节点
    if children != "null":
        #当前节点的属性名称下标
        featKey = copy.deepcopy( firstStr)
        labelIndex = labels.index(featKey)   #featKey =opy.deepcopy(firstStr)   labelIndex = labels.index(featKey)   #特征在labels中的下标
        #print("->",inputTree,"\n->",labelIndex)
                
        #用于递归的子labels
        subLabels = labels[:]            #subLabels = copy.deepcopy(labels) #子labels
        #像树构造一样将本节点的label删除，这个属性遍历完毕
        '''
        if labelIndex != "null":
            print(labelIndex)
            print("->",labels)
            del(labels[labelIndex])          #del(labels[labelIndex])   删除本节点特征
        '''
        
        #右孩子
        threshold = re.findall(r"\d+\.?\d*",children[1]['text'])[0]
        subDataSet = splitDataSet(dataSet,labelIndex,float(threshold),"lt")
        subTestSet = splitDataSet(testData,labelIndex,float(threshold),"lt")
        if len(subDataSet) > 0 and len(subTestSet) > 0:
            inputTree["children"][1] = pruningTree(children[1],subDataSet,subTestSet,subLabels,weight)

        #左孩子
        threshold = re.findall(r"\d+\.?\d*",children[0]['text'])[0]  
        subDataSet = splitDataSet(dataSet,labelIndex,float(threshold),"gt")
        subTestSet = splitDataSet(testData,labelIndex,float(threshold),"gt")
        if len(subDataSet) > 0 and len(subTestSet) > 0:
            inputTree["children"][0] = pruningTree(children[0],subDataSet,subTestSet,subLabels,weight)
    
        print("误差，测试集和剪枝后集合",calcTestErr(inputTree,testData,subLabels) ,"\n",testMajor(majorityCnt(classList),testData))    
        if calcTestErr(inputTree,testData,subLabels) < weight*testMajor(majorityCnt(classList),testData):
            if inputTree["children"][0]["name"] == inputTree["children"][1]["name"]:
                return {'name':majorityCnt(classList),'col':'null','text':inputTree['text'],'children':'null'}
            # 剪枝后的误差反而变大，不作处理，直接返回
            return inputTree#1.675
        else:
            # 剪枝，原父结点变成子结点，其类别由多数表决法决定
            return {'name':majorityCnt(classList),'col':'null','text':inputTree['text'],'children':'null'}
    return inputTree


#-------------------------X.总控制函数()------------------------------
#生成树，预测单条，预测多条，计算精度
#--------------------------------------------------------------------
#生成CART树
#输入:dataSource:{csv,db} sourceName:{csv,db.table} fields{}   target:{tree,json}
#输出:根据target输出tree,json,训练集精度,训练集大小,运行时间
def GenerateCART(dataSource="db",sourceName="db_slg.iri_train",fields=[],target="dictTree",pruning="none",outSourceName="db_slg.iri_test"):
    '''常用变量定义'''
    #数据集合(二维数组)
    sourceDataSet = []
    #数据表头/特征名(一维数组)
    labels = []
    #字典树
    dictTree = {}
    DictTrees = []
    ACC = 0.0
    ACCIndex = 0
    
    datasize = 0
    costtime = 0.0
    trainACC = 0.0
 
    '''数据源读取'''
    if dataSource == 'csv':
        sourceDataSet,labels = readFromCSV(sourceName)
    elif dataSource == "db":
        dbname = sourceName.split('.')[0]
        tablename = sourceName.split('.')[1]
        sourceDataSet,labels = readFromDB(dbname,tablename,fields)
        if pruning == "outpruning":
            outdbname = outSourceName.split('.')[0]
            outtablename = outSourceName.split('.')[1]
            outtestData,labels = readFromDB(outdbname,outtablename,fields)   
    elif dataSource == "list":
        sourceDataSet = sourceName
        labels = fields
    else:
        return {"message":"please specify the dataSource, csv or db" }

    '''树训练,将循环5次找到最佳模型，三种剪枝模式由高层指定'''    
    #五次循环找最佳
    for i in range(5):        
        #内剪枝只有内部测试集精度
        #内部交叉验证剪枝,需要切分数据集,使用内部测试数据集合训练
        if pruning == "inpruning":
            dataSet,intestData = createCVDataSet(sourceDataSet,some_list=[0,1],probabilities=[0.75,0.25])
            #生成
            starttime = datetime.datetime.now()
            
            dictTree = createTree(dataSet,labels,"null")
            
            endtime = datetime.datetime.now()

            #剪枝
            print("内剪枝之前:",json.dumps(dictTree))
            pruningTree(dictTree,dataSet,intestData,labels)
            #评测
            trainACC,result = checkAccuracy(dictTree,dataSet,labels)
            testACC,result = checkAccuracy(dictTree,intestData,labels)
        #外剪枝需要外部测试集，但是不会将其记入树的字段当中，这只是一个评测好模型的手段
        elif pruning == "outpruning":
            dataSet = sourceDataSet
            #生成
            starttime = datetime.datetime.now()
            
            dictTree = createTree(dataSet,labels,"null")
            
            endtime = datetime.datetime.now()
            print('外剪枝之前',json.dumps(dictTree))
            pruningTree(dictTree,dataSet,outtestData,labels)
            #评测
            trainACC,result = checkAccuracy(dictTree,dataSet,labels)
            testACC,result = checkAccuracy(dictTree,outtestData,labels)
        #无剪枝则训练精度越高越好
        else:
            dataSet = sourceDataSet
            #生成
            starttime = datetime.datetime.now()
            
            dictTree = createTree(dataSet,labels,"null")
            
            endtime = datetime.datetime.now()
            #评测
            trainACC,result = checkAccuracy(dictTree,dataSet,labels)
            testACC = 0.0
            
        datasize = len(dataSet)
        costtime = (endtime - starttime).total_seconds()*1000
        #存入数组评测
        DictTrees.append((dictTree,datasize,costtime,trainACC,testACC))
        
        print("第",i,"棵树:\n",DictTrees)
        #只有树的根节点有孩子时才能通过验证
        if ((1-TESTACC_PROP)*trainACC+TESTACC_PROP*testACC > ACC) and (dictTree["children"] != "null"):
            ACC = (1-TESTACC_PROP)*trainACC+TESTACC_PROP*testACC
            ACCIndex = i

    '''树输出'''
    print("\n------------------总情况概览---------------------:\n",DictTrees)
    #返回顺序是 字典树，参与构建树的数据集大小，生成时间，训练集精度[，测试集精度(用不到)]
    if target == "dictTree":
        print('-------------------------构造完毕:dictTree:----------------------------\n',json.dumps(dictTree))
        return DictTrees[ACCIndex][:-1]
    elif target == "json":
        print('-------------------------构造完毕:json:----------------------------\n',json.dumps(dictTree))         
        return json.dumps(DictTrees[ACCIndex][0]),DictTrees[ACCIndex][1],DictTrees[ACCIndex][2],DictTrees[ACCIndex][3]
    else:
        return {"message":"please specify the target, dictTree，biTree or json"},datasize,costtime,trainACC

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
    return checkAccuracy(dictTree,dataSet,labels)    
    
#----------------------模块直接执行--------------------------
if __name__ == '__main__':
    '''
    DictTrees = []    
    ACC = 0.0
    ACCIndex = 0
    fields=[]
    for i in range(5):
        dictTree = GenerateCART(dataSource="db",sourceName="db_dataset.iri_train",fields=fields,target="dictTree",pruning="none",outSourceName="db_dataset.iri_test")
        trainACC,results = CheckAccuracy(dictTree,dataSource="db",sourceName="db_dataset.iri_train",fields=fields)        
        testACC,results = CheckAccuracy(dictTree,dataSource="db",sourceName="db_dataset.iri_test",fields=fields)
        DictTrees.append((dictTree,trainACC,testACC))
        print("原训练：",trainACC,"原测试：",testACC)
        if 0.4*trainACC+0.6*testACC > ACC:
            ACC = 0.4*trainACC+0.6*testACC
            ACCIndex = i
    print("第",ACCIndex,"个最优",json.dumps(DictTrees[ACCIndex][0]))
    print("原训练：",DictTrees[ACCIndex][1],"原测试：",DictTrees[ACCIndex][2])
    '''
    
    
    import datetime
    
    DictTrees = []
    ACC = 0.0
    ACCIndex = 0
    fields=['English','CET4','CET6','AdvancedMath','LinearAlgebra','ProbabilityTheory','DataStructure','DataBase','OperatingSystem','CppProgramming','ProgrammingPractice','JavaProgramming','COM_VC2']
    for i in range(5):
        dictTree,datasize,costtime,trainACC = GenerateCART(dataSource="db",sourceName="db_dataset.15级计算机专业个人成绩表_train",fields=fields,target="dictTree",pruning="inpruning",outSourceName="db_dataset.15级计算机专业个人成绩表_test")
            
        testACC,results = CheckAccuracy(dictTree,dataSource="db",sourceName="db_dataset.15级计算机专业个人成绩表_test",fields=fields)
        DictTrees.append((dictTree,datasize,costtime,trainACC,testACC))        
        print("第",i,DictTrees)
        if (1-TESTACC_PROP)*trainACC+(TESTACC_PROP)*testACC > ACC:
            ACC = (1-TESTACC_PROP)*trainACC+(TESTACC_PROP)*testACC
            ACCIndex = i
    print(DictTrees[ACCIndex][0],"数据量:",DictTrees[ACCIndex][1],"时间:",DictTrees[ACCIndex][2],"ms 训练精度:",DictTrees[ACCIndex][3],"测试精度:",DictTrees[ACCIndex][4],)
