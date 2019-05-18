'''
标准C45算法脚本

输入：
    1. 从1个第0行为特征名，其余行为数据的csv文件读入
    2. 从数据库读入
输出:
    1. 生成一个json字符串
    2. 可以打开浏览器展示图片
    3. 可以生成一条sql插入树信息到指定数据库
特性:
    1. 自动判断数据集为连续型或是离散型(连续型/离散型不允许有任何一列是离散型/连续型的)
    2. 通过调用两个C45算法模块实现上述功能
'''


import json
from math import log
import re
import copy
import pymysql
import copy
import datetime
import pdb
inf = 9999999999999


DBHOST = "47.95.196.25"
DBUSER = "root"
DBPWD = "12345678"

#内部交叉验证测试集比例
SPLIT_PROP = 0.25
#评价模型测试正确率所占比
TESTACC_PROP = 0.6
#剪枝时剪枝后误差比重（值越大剪枝数越少）
WEIGHT = 1#1.675

diguiceshu = 2

#------------------------I.数据读取----------------------------
# I. 从一个DB读取数据判断是否为离散型
def identifyType_db(dbname="db_dataset",tablename='lenses_one',fields=[]):
    print("``````````C45_Standard.py```````````````````\nin identifyType_db() , use %s . %s " % (dbname,tablename), "\nfields:\n" ,fields)
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
        #print(type(value),"\nis?",is_number(value))
        if value == '-' or is_number(value):
            pass
        else:
            return "Discrete"
    return "Continuous"

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

# I.2 从一个DB读取数据判断是否为离散型
def readFromDB(dbname="db_dataset",tablename='lenses_one',fields=[],decisionTreeType="Discrete"):    
    db=pymysql.connect(DBHOST,DBUSER,DBPWD,dbname,charset="utf8")
    cur = db.cursor()
    if fields == []:
        #如果fields为空，则直接取出数据库中所有不是id的字段
        querySql = "select COLUMN_NAME from information_schema.COLUMNS where table_name = '%s' and COLUMN_NAME not like '%%id' " % (tablename)
        print("querySql:" , querySql)
        cur.execute(querySql)
        for value in cur.fetchall():
            fields.append(value[0])  
        print("fields:" , fields)
        
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
            if decisionTreeType =='Discrete':            
                if dataSet[i][j] == '-':
                    dataSet[i][j] = 'failed'
            elif decisionTreeType =='Continuous':
                if dataSet[i][j] == '-':
                    dataSet[i][j] = 0.0
                dataSet[i][j] = float(dataSet[i][j])
        if is_number(dataSet[i][-1]):
            dataSet[i][-1] = resultDiscretization(dataSet[i][-1])
    #这里根据dataset数据列数来决定labels裁剪，总比dataset列数少1
    labels = fields[:len(dataSet[0])-1]
    print("\n------------------------------SQL:------------------------------\n",sql,
          "\n--------------------------前10条dataSet:---------------------\n",dataSet[0],
          "\n-----------------------------Labels:----------------------------\n",labels)
    return dataSet,labels

# I.3 从一个有表头的csv文件读取数据判断是否为离散型
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
# I.4 从一个有表头的csv文件读取数据
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


#------------------------II.树核心构建算法----------------------------

def calcShannonEnt(dataSet):
    """
    输入：数据集
    输出：数据集的香农熵
    描述：计算给定数据集的香农熵；熵越大，数据集的混乱程度越大
    """
    numEntries = len(dataSet)
    labelCounts = {}
    for featVec in dataSet:
        currentLabel = featVec[-1]
        if currentLabel not in labelCounts.keys():
            labelCounts[currentLabel] = 0
        labelCounts[currentLabel] += 1
    shannonEnt = 0.0
    for key in labelCounts:
        prob = float(labelCounts[key])/numEntries
        shannonEnt -= prob * log(prob, 2)
    return shannonEnt

def splitDataSet_dis(dataSet, axis, value):
    """
    输入：数据集，选择维度，选择值
    输出：划分数据集
    描述：按照给定特征划分数据集；去除选择维度中等于选择值的项
    """
    retDataSet = []
    for featVec in dataSet:
        if featVec[axis] == value:
            reduceFeatVec = featVec[:axis]
            reduceFeatVec.extend(featVec[axis+1:])
            retDataSet.append(reduceFeatVec)
    return retDataSet

# 划分数据集, axis:按第几个特征划分, value:划分特征的值, LorR: value值左侧（小于）或右侧（大于）的数据集
def splitDataSet(dataSet, axis, value, LorR='L'):
    retDataSet = []
    featVec = []
    if LorR == 'L':
        for featVec in dataSet:
            if float(featVec[axis]) <= value:
                retDataSet.append(featVec)
    else:
        for featVec in dataSet:
            if float(featVec[axis]) > value:
                retDataSet.append(featVec)
    return retDataSet

#feature is exhaustive, reture what you want label
def majorityCnt(classList):
    classCount = {}
    for vote in classList:
        if vote not in classCount.keys():
            classCount[vote] = 0
        classCount[vote] += 1
    return max(classCount,key=classCount.get)

# 选择最好的数据集划分方式
def chooseBestFeatureToSplit(dataSet, labelProperty):
    ##pdb.set_trace()
    numFeatures = len(labelProperty)  # 特征数
    baseEntropy = calcShannonEnt(dataSet)  # 计算根节点的信息熵
    bestInfoGain = 0.0
    bestFeature = -1
    bestPartValue = None  # 连续的特征值，最佳划分值
    #print("in chooseBestFeatureToSplit",len(dataSet[0]))
    #print("dataSet:\n",dataSet)
    #print("numFeatures:",numFeatures)
    for i in range(numFeatures):  # 对每个特征循环
        featList = [example[i] for example in dataSet]
        uniqueVals = set(featList)  # 该特征包含的所有值
        newEntropy = 0.0
        bestPartValuei = None
        if labelProperty[i] == 0:  # 对离散的特征
            for value in uniqueVals:  # 对每个特征值，划分数据集, 计算各子集的信息熵
                subDataSet = splitDataSet_dis(dataSet, i, value)
                prob = len(subDataSet) / float(len(dataSet))
                newEntropy += prob * calcShannonEnt(subDataSet)
        else:  # 对连续的特征
            sortedUniqueVals = list(uniqueVals)  # 对特征值排序
            sortedUniqueVals.sort()
            listPartition = []
            minEntropy = inf
            ##pdb.set_trace()
            for j in range(len(sortedUniqueVals) - 1):  # 计算划分点
                partValue = (float(sortedUniqueVals[j]) + float(
                    sortedUniqueVals[j + 1])) / 2
                # 对每个划分点，计算信息熵
                dataSetLeft = splitDataSet(dataSet, i, partValue, 'L')
                dataSetRight = splitDataSet(dataSet, i, partValue, 'R')
                probLeft = len(dataSetLeft) / float(len(dataSet))
                probRight = len(dataSetRight) / float(len(dataSet))
                Entropy = probLeft * calcShannonEnt(
                    dataSetLeft) + probRight * calcShannonEnt(dataSetRight)
                if Entropy < minEntropy:  # 取最小的信息熵
                    minEntropy = Entropy
                    bestPartValuei = partValue
            newEntropy = minEntropy
        infoGain = baseEntropy - newEntropy  # 计算信息增益
        if infoGain > bestInfoGain:  # 取最大的信息增益对应的特征
            bestInfoGain = infoGain
            ##pdb.set_trace()
            #print("bestFeature:",i,"bestPartValue",bestPartValue)
            bestFeature = i
            bestPartValue = bestPartValuei
    return bestFeature, bestPartValue

# 创建树, 样本集 特征 特征属性（0 离散， 1 连续）
def createTree(dataSet, labels, labelProperty,text):
    ##pdb.set_trace()
    #print("DDD:",dataSet,"\n",labels,"\n", labelProperty)
    #print("DDD:",len(dataSet[0]),"\n",len(labels),"\n", len(labelProperty))
    classList = [example[-1] for example in dataSet]  # 类别向量
    if classList.count(classList[0]) == len(classList):  # 如果只有一个类别，返回
        #return classList[0]
        return {"name":classList[0],"col":"null","text":text,"children":"null"}
    if len(dataSet[0]) == 1:  # 如果所有特征都被遍历完了，返回出现次数最多的类别
        #return majorityCnt(classList)
        return {"name":majorityCnt(classList),"col":"null","text":text,"children":"null"}
    bestFeat, bestPartValue = chooseBestFeatureToSplit(dataSet,labelProperty)  # 最优分类特征的索引
    if bestFeat == -1:  # 如果无法选出最优分类特征，返回出现次数最多的类别
        return {"name":majorityCnt(classList),"col":"null","text":text,"children":"null"}
    if labelProperty[bestFeat] == 0:
        # 对离散的特征
        bestFeatLabel = labels[bestFeat]
        #myTree = {bestFeatLabel: {}}
        myTree = {"name":bestFeatLabel,"col":bestFeat,"text":text,"children":[]}
        labelsNew = copy.copy(labels)
        labelPropertyNew = copy.copy(labelProperty)
        del(labelsNew[bestFeat])  # 已经选择的特征不再参与分类
        del(labelPropertyNew[bestFeat])
        featValues = [example[bestFeat] for example in dataSet]
        uniqueValue = set(featValues)  # 该特征包含的所有值
        for value in uniqueValue:  # 对每个特征值，递归构建树
            subLabels = labelsNew[:]
            subLabelProperty = labelPropertyNew[:]
            myTree["children"].append(createTree(splitDataSet_dis(dataSet,bestFeat,value),subLabels,subLabelProperty,value))
    else:
        ##pdb.set_trace()
        #对连续的特征，不删除该特征，分别构建左子树和右子树
        #print("labels",labels,"\nbestFeat:",bestFeat,"\nlabels长度:",len(labels))
        bestFeatLabel = labels[bestFeat]

        #+ '<' + str(bestPartValue)
        #myTree = {bestFeatLabel: {}}
        myTree = {"name":bestFeatLabel,"col":bestFeat,"text":text,"children":[{},{}]}
        subLabels = labels[:]
        subLabelProperty = labelProperty[:]
        # 构建左子树
        valueLeft = '<='+str(bestPartValue) #'是'
        myTree["children"][1] =createTree(splitDataSet(dataSet, bestFeat,bestPartValue,'L'), subLabels,subLabelProperty,valueLeft)

        # 构建右子树
        valueRight = '>'+str(bestPartValue) #'否'
        myTree["children"][0] =createTree(splitDataSet(dataSet, bestFeat,bestPartValue,'R'), subLabels,subLabelProperty,valueRight)
    return myTree


#------------------------III.分类和属性----------------------------
#III.1 注意连续型分类不同于离散型
def classify(jsonTree,labels,observation,decisionTreeType):
    #如果是叶子节点
    if jsonTree["children"]=="null":
        return jsonTree["name"]
    #是分支节点
    else:
        if decisionTreeType == "Continuous":
            ##pdb.set_trace()
            #找到本节点属性列对应的属性值
            v=float(observation[nameToIndex(labels,jsonTree['name'])])
            #v=float(observation[jsonTree["col"]])
            #nameToIndex(jsonTree['name'],labels)]
            branch=None
            #如果这个值符合节点的子节点的分支上的引导文字中指定的数字范围
            threshold = re.findall(r"\d+\.?\d*",jsonTree["children"][0]["text"])[0]
            if v > float(threshold):
                branch=jsonTree["children"][0]
            else:
                branch=jsonTree["children"][1]
            
        elif decisionTreeType == "Discrete":
            #找到本节点属性列对应的属性值
            v=observation[nameToIndex(labels,jsonTree['name'])]#        
            #print("科目:",jsonTree['name'])
            #print("-->",nameToIndex(labels,jsonTree['name']))
            #print("source from:",observation)
            branch=None
            #如果这个值就是节点的子节点的分支上的引导文字
            #print("==>",jsonTree["children"])
            for i in range(len(jsonTree["children"])):            
                #print("i=",i," v:",v,"\n","jsonTree",jsonTree["children"][i]["text"])
                if v==jsonTree["children"][i]["text"]:             
                    branch=jsonTree["children"][i]                    
                    break
        else:
            print("no Type")
        #如果这个分类标签在训练集合中并没有那么只能随便选了
        if branch == None:
            branch = jsonTree["children"][0]
        return classify(branch,labels,observation,decisionTreeType)

#辅助函数，根据列名确定列号
def nameToIndex(labels,name):
    for i in range(len(labels)):
        if name == labels[i]:
            return i
    return 0


def checkAccuracy(jsonTree,observations,labels,decisionTreeType): 
    total = float(len(observations))
    if total <= 0:
        return 0
    correct = 0.0
    classes = []
    #仅用于输出
    counts = 0
    for observation in observations:    
        result = classify(jsonTree,labels,observation,decisionTreeType)        
        classes.append(result)
        if str(result) == str(observation[-1]):
            correct += 1.0
        #仅用于输出
        if counts < 10:
            #print("line:",observation[:-1])
            #print("result: 真实:",observation[-1],"|预测:",result)
            counts += 1
    return correct/total,classes


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

#------------------------IV.剪枝------------------------------
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
def calcTestErr(myTree,testData,labels,decisionTreeType):
    errorCount = 0.0
    for i in range(len(testData)): 
        if classify(myTree,labels,testData[i],decisionTreeType) != testData[i][-1]:
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
def pruningTree(inputTree,dataSet,testData,labels,weight=WEIGHT,decisionTreeType="Continuous",depth=1):
    #pdb.set_trace()
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
        labelIndex = labels.index(featKey)
        #print("为何是10?",len(labels),"\n",labels,"\n",featKey,"\n",labels.index(featKey))
        #用于递归的子labels
        subLabels = labels[:]         
        
        #pdb.set_trace()
        
        #离散型是多叉树
        if decisionTreeType == "Discrete":
            if labelIndex != "null":
                del(labels[labelIndex])          #del(labels[labelIndex])   删除本节点特征
            
            for i in range(len(children)):
                threshold = children[i]["text"]
                subDataSet = splitDataSet_dis(dataSet, labelIndex, threshold)
                subTestSet = splitDataSet_dis(testData,labelIndex,threshold)
                if len(subDataSet) > 0 and len(subTestSet) > 0:
                    inputTree["children"][i] = pruningTree(children[i],subDataSet,subTestSet,copy.deepcopy(labels),weight,decisionTreeType)
            
            print("误差，测试集和剪枝后集合",calcTestErr(inputTree,testData,subLabels,decisionTreeType) ," ",testMajor(majorityCnt(classList),testData))               
            if calcTestErr(inputTree,testData,subLabels,decisionTreeType) < testMajor(majorityCnt(classList),testData):
                # 剪枝后的误差反而变大，不作处理，直接返回
                return inputTree 
            else:
                # 剪枝，原父结点变成子结点，其类别由多数表决法决定
                return {'name':majorityCnt(classList),'col':'null','text':inputTree['text'],'children':'null'}

        elif decisionTreeType == "Continuous":
            #pdb.set_trace()
            #右孩子
            threshold = re.findall(r"\d+\.?\d*",children[1]['text'])[0]
            subDataSet = splitDataSet(dataSet,labelIndex,float(threshold),"L")
            subTestSet = splitDataSet(testData,labelIndex,float(threshold),"L")
            if len(subDataSet) > 0 and len(subTestSet) > 0:
                inputTree["children"][1] = pruningTree(children[1],subDataSet,subTestSet,subLabels,weight,decisionTreeType,depth+1)

            #左孩子
            threshold = re.findall(r"\d+\.?\d*",children[0]['text'])[0]  
            subDataSet = splitDataSet(dataSet,labelIndex,float(threshold),"R")
            #print("subTest splitDataSet:",len(dataSet[0]),"\n",labelIndex,"\n",float(threshold))
            subTestSet = splitDataSet(testData,labelIndex,float(threshold),"R")
            if len(subDataSet) > 0 and len(subTestSet) > 0:
                inputTree["children"][0] = pruningTree(children[0],subDataSet,subTestSet,subLabels,weight,decisionTreeType,depth+1)
        
            print("误差，测试集和剪枝后集合",calcTestErr(inputTree,testData,subLabels,decisionTreeType) ," ",testMajor(majorityCnt(classList),testData))    
            if calcTestErr(inputTree,testData,subLabels,decisionTreeType) < weight*testMajor(majorityCnt(classList),testData):
                if inputTree["children"][0]["name"] == inputTree["children"][1]["name"]:
                    return {'name':majorityCnt(classList),'col':'null','text':inputTree['text'],'children':'null'}
                # 剪枝后的误差反而变大，不作处理，直接返回
                if depth > 4:
                    return {'name':majorityCnt(classList),'col':'null','text':inputTree['text'],'children':'null'}
                return inputTree#1.675
            else:
                # 剪枝，原父结点变成子结点，其类别由多数表决法决定
                return {'name':majorityCnt(classList),'col':'null','text':inputTree['text'],'children':'null'}
    #pdb.set_trace()
    return inputTree     



#----------------------X.总控函数()--------------------------
class C45:
    '''常用变量定义'''
    #数据集合(二维数组)
    sourceDataSet = []
    #数据表头/特征名(一维数组)
    labels = []
    #数据库字段选择器
    bakFields = []
    fields = []
    #决策树类型(离散型Discrete/连续型Continuous)
    decisionTreeType = ""
    typeList = []
    #数据集合
    dataSource="csv"
    #数据源名称
    sourceName=""
    #目标类型{"dictTree,json,biTree,db"}
    target="dictTree"
    #字典树
    dictTree = {}
    datasize = 0
    costtime = 0.0
    trainACC = 0.0

    def __init__(self,dataSource="csv",sourceName="db_dataset.lenses_one",fields=[]):
        #数据集合
        self.dataSource=dataSource
        #数据源名称
        self.sourceName=sourceName
        self.fields = fields
        self.bakFields = fields
        '''读取数据判断类型'''
        if dataSource == 'csv':
            self.decisionTreeType = identifyType_csv(sourceName)
            self.sourceDataSet,self.labels = readFromCSV(sourceName)
            #为了防止labels少属性情况
            self.fields = self.labels
        elif dataSource == "db":            
            dbname = sourceName.split('.')[0]
            tablename = sourceName.split('.')[1]
            self.decisionTreeType = identifyType_db(dbname,tablename,fields)                     
            self.sourceDataSet,self.labels = readFromDB(dbname,tablename,fields,self.decisionTreeType)
            #为了防止labels少属性情况
            self.fields = self.labels
        else:
            return {"message":"please specify the dataSource, csv or db" }
        if self.decisionTreeType == "Discrete":
            self.typeList = [0 for _ in range(len(self.fields))]            
        elif self.decisionTreeType == "Continuous":
            self.typeList = [1 for _ in range(len(self.fields))]


    def GenerateC45(self,target="dictTree",pruning="none",pruningWeight=WEIGHT,outSourceName="db_dataset.15级计算机专业个人成绩表_test"):
        DictTrees = []
        ACC = 0.0
        ACCIndex = -1

        datasize = 0
        costtime = 0.0
        trainACC = 0.0
        outtestData = []
        
        if pruning == "outpruning":
            outdbname = outSourceName.split('.')[0]
            outtablename = outSourceName.split('.')[1]            
            outtestData,swaplabels = readFromDB(outdbname,outtablename,self.bakFields,self.decisionTreeType)  
        
        #五次循环找最佳
        for i in range(15):        
            sourceDataSet = self.sourceDataSet     
            typeList = self.typeList
            #labels = self.fields
            labels =  copy.deepcopy(self.fields)
            decisionTreeType= self.decisionTreeType
            
            #内剪枝只有内部测试集精度
            #内部交叉验证剪枝,需要切分数据集,使用内部测试数据集合训练
            if pruning == "inpruning":
                dataSet,intestData = createCVDataSet(sourceDataSet,some_list=[0,1],probabilities=[0.75,0.25])
                #生成
                starttime = datetime.datetime.now()

                dictTree = createTree(dataSet,labels,typeList,"null")
                
                endtime = datetime.datetime.now()

                #剪枝
                print("内剪枝之前:",json.dumps(dictTree))
                pruningTree(dictTree,dataSet,intestData,labels,pruningWeight,decisionTreeType)
                #评测
                trainACC,result = checkAccuracy(dictTree,dataSet,labels,decisionTreeType)
                testACC,result = checkAccuracy(dictTree,intestData,labels,decisionTreeType)
                print("---------------------------------------------------------------")
            #外剪枝需要外部测试集，但是不会将其记入树的字段当中，这只是一个评测好模型的手段
            elif pruning == "outpruning":
                dataSet = sourceDataSet
                #生成
                starttime = datetime.datetime.now()
                
                dictTree = createTree(dataSet,labels,typeList,"null")
                
                endtime = datetime.datetime.now()

                pruningTree(dictTree,dataSet,outtestData,labels,pruningWeight,decisionTreeType)
                #评测
                trainACC,result = checkAccuracy(dictTree,dataSet,labels,decisionTreeType)
                testACC,result = checkAccuracy(dictTree,outtestData,labels,decisionTreeType)
            #无剪枝则训练精度越高越好
            else:
                dataSet = sourceDataSet
                #生成
                starttime = datetime.datetime.now()
                
                dictTree = createTree(dataSet,labels,typeList,"null")
                
                endtime = datetime.datetime.now()
                #评测
                trainACC,result = checkAccuracy(dictTree,dataSet,labels,decisionTreeType)
                testACC = 0.0
                
            datasize = len(dataSet)
            costtime = (endtime - starttime).total_seconds()*1000
            #存入数组评测
            DictTrees.append((dictTree,datasize,costtime,trainACC,testACC))
            
            print("第",i,"棵树:\n",DictTrees)
            #只有树的根节点有孩子时才能通过验证
            nodenums = json.dumps(dictTree).count('"name"')
            print("^^^^^^^^:",nodenums)
            #多于12个节点的不要
            if (pruning == 'inpruning' or pruning == 'outpruning' ) and ( nodenums > 21 or nodenums <= 6):
                continue
            elif ((1-TESTACC_PROP)*trainACC+TESTACC_PROP*testACC > ACC) and (dictTree["children"] != "null"):
                ACC = (1-TESTACC_PROP)*trainACC+TESTACC_PROP*testACC
                ACCIndex = i
            print("&&&&&&",ACCIndex)
        
        
            '''树输出'''
        print("\n------------------总情况概览---------------------:\n",DictTrees)
        print(ACCIndex)
        global diguiceshu
        if (pruning == 'inpruning' or pruning == 'outpruning' ) and (ACCIndex == -1) and (diguiceshu > 0):
            diguiceshu -= 1
            #自动调整权值,节点数目太大，需要调小权值
            if nodenums > 21:
                return self.GenerateC45(target,pruning,pruningWeight-0.1,outSourceName)
            elif nodenums <= 6 :
                return self.GenerateC45(target,pruning,pruningWeight+0.1,outSourceName)
            else:
                return self.GenerateC45(target,pruning,pruningWeight,outSourceName)
        self.dictTree,self.datasize,self.costtime,self.trainACC,testACC = DictTrees[ACCIndex]
        #如果指定返回dictTree
        if target == "dictTree":
            print('-------------------------dictTree:----------------------------\n',json.dumps(DictTrees[ACCIndex][0]))
            return DictTrees[ACCIndex][0]
        #默认就返回json
        else:
            print('-------------------------json:----------------------------\n',json.dumps(DictTrees[ACCIndex][0])) 
            return json.dumps(DictTrees[ACCIndex][0])
    
    def CalcProperties(self):
        #树深度则需要递归得出
        self.depth = getTreeDepth(self.dictTree) + 1
        #节点数直接通过统计字符串中'name'个数
        jsonTree = json.dumps(self.dictTree)
        self.nodes_num = jsonTree.count('"name"')
        return self.decisionTreeType,self.nodes_num,self.depth,self.datasize,self.costtime,self.trainACC
    '''
    def Classify(self,observation):        
        #fields可能会少属性
        resultDict = classify(self.dictTree,self.fields,observation,self.decisionTreeType)
        print(observation , " => ",resultDict)
        return resultDict

    def ClassifyAll(self,observations):
        classes = []
        for observation in observations:
            classes.append(Classify(self.dictTree,observation))        
        print(observations , " => ",classes)
        return classes

    def CheckAccuracy(self,dataSource='db',sourceName="db_dataset.lenses_one",fields=[]):
        #数据源读取
        if dataSource == 'csv':
            dataSet,labels = readFromCSV(sourceName)
        elif dataSource == "db":
            dbname = sourceName.split('.')[0]
            tablename = sourceName.split('.')[1]
	    print(dbname,tablename,fields,self.decisionTreeType)
            dataSet,labels = readFromDB(dbname,tablename,fields,self.decisionTreeType)          
        elif dataSource == "list":
            dataSet = sourceName
        else:
            return {"message":"please specify the dataSource, csv or db" }
        
        print('----------------CheckAccuracy DataSet(top10):-------------------\n',dataSet[:10],'\n')
        return checkAccuracy(self.dictTree,labels,dataSet,self.decisionTreeType)    
    '''

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
    #该静态方法传入树,labels,观测变量,决策树数据类型，才可以可进行分类（类型逻辑实现在函数内实现）
    def Classify(dictTree,fields,observation,decisionTreeType):
        #fields可能会少属性
        resultDict = classify(dictTree,fields,observation,decisionTreeType)
        print(observation , " => ",resultDict)
        return resultDict
    
     
    @staticmethod
    #该静态方法传入树,labels,观测变量,决策树数据类型，才可以可进行分类（类型逻辑实现在函数内实现）
    def ClassifyAndAnalysis(dictTree,dataSource='db',sourceName="db_dataset.lenses_one",fields=[],decisionTreeType="Discrete"):
        #数据源读取
        if dataSource == 'csv':
            dataSet,labels = readFromCSV(sourceName)
        elif dataSource == "db":
            dbname = sourceName.split('.')[0]
            tablename = sourceName.split('.')[1]
            dataSet,labels = readFromDB(dbname,tablename,fields,decisionTreeType)          
        elif dataSource == "list":
            dataSet = sourceName
        else:
            return {"message":"please specify the dataSource, csv or db"}
        
        print('----------------CheckAccuracy DataSet(top10):-------------------\n',dataSet[:10],'\n')
        #这里的labels不用担心在类生成之后损坏，所以fields为空也好，不为空也好，labels始终可以作为分类的参考域名集
        return checkAccuracy(dictTree,dataSet,labels,decisionTreeType) 



    def DrawTree(self):
        import os,json
        cmd = "firefox 'http://api.crepuscule.xyz/weixinapi/drawtree?json="
        cmd += json.dumps(self.dictTree)
        cmd += "'"
        #print(cmd)
        os.system(cmd)

#----------------------模块直接执行--------------------------
if __name__ == '__main__':
  
    #fields=['English','CET4','CET6','AdvancedMath','LinearAlgebra','ProbabilityTheory','DataStructure','DataBase','OperatingSystem','CppProgramming','ProgrammingPractice','JavaProgramming','COM_VC2']
    fields = ["English","CET4","AdvancedMath","LinearAlgebra","ProbabilityTheory","Programming","ProgrammingPractice","COM_MS"]
    control = C45('db',"db_dataset.train_15_transcripts_nocs",fields=fields)
    dictTree = control.GenerateC45('dictTree','inpruning',0.8,'db_dataset.test_15_transcripts_nocs')
    print(control.CalcProperties())
    testACC = control.ClassifyAndAnalysis(dictTree,'db','db_dataset.test_15_transcripts_nocs',fields,"Continuous")
    print(testACC[0])
    
    print(control.GenerateIfThen(dictTree,(control.CalcProperties())[0]))
