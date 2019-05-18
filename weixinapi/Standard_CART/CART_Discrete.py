'''CART_Discrete.py'''
import pymysql
import json
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
WEIGHT = 1.8#.675

'''
基本功能:[ok]

需要深入理解的问题:

2. 不纯度计算是否正确,二叉树创树功能理解
3. 更加深入的决策树的评定方法(单纯的精度太单薄)
'''

#--------------------------I. 数据读取--------------------------------
# I.1 从一个有表头的csv文件读取数据
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

# I.2 从一个DB读取数据,并指定参与预测的属性域
def readFromDB(dbname="db_dataset",tablename='paly',fields=[]):
    print("````````````````CART_Discrete.py``````````````````````\nin readFromDB() , use %s . %s " % (dbname,tablename), "\nfields:\n" ,fields)
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
                dataSet[i][j] = 'failed'
    #这里根据dataset数据列数来决定labels裁剪，总比dataset列数少1
    labels = fields[:len(dataSet[0])-1]
    print("\n------------------------------SQL:------------------------------\n",sql,
          "\n--------------------------前10条dataSet:---------------------\n",dataSet[:10],
          "\n-----------------------------Labels:----------------------------\n",labels)
    return dataSet,labels



#-------------------II. 决策树生成核心算法------------------------
#II.1 决策树的节点类
class decisionnode:
    def __init__(self,col=-1,colName="",value=None,results=None,tb=None,fb=None):
        self.col=col                #待检测条件所属的列索引。即当前是对第几列数据进行分类
        self.colName=colName
        self.value=value            #为使结果为true，当前列必须匹配的值
        self.results=results        #如果当前节点时叶节点，表示该节点的结果值，如果不是叶节点，为None
        self.tb=tb                  #判断条件为true后的子节点
        self.fb=fb                  #判断调节为false后的子节点

#II.2 拆分数据集合
# 根据某一属性对数据集合进行拆分，能够处理数值型数据或名词性数据。其实决策树只能处理离散型数据，对于连续性数据也是划分为范围区间块
# rows样本数据集，column要匹配的属性列索引，value指定列上的数据要匹配的值
def divideset(rows,column_index,column_value):
    # 定义一个函数，令其告诉我们数据行属于第一组（返回值为true）还是第二组（返回值false）
    split_function=None
    if isinstance(column_value,int) or isinstance(column_value,float):
        split_function=lambda row:row[column_index]>=column_value   #按大于、小于区分
    else:
        split_function=lambda row:row[column_index]==column_value   #按等于、不等于区分

    # 将数据集拆分成两个子集，并返回
    set1=[row for row in rows if split_function(row)]
    set2=[row for row in rows if not split_function(row)]
    return (set1,set2)

#II.3 计算基尼不纯度
#rows样本数据集
def giniimpurity(rows):
    total=len(rows)
    counts=uniquecounts(rows)
    imp=0
    for k1 in counts:
        p1=float(counts[k1])/total
        for k2 in counts:
            if k1==k2: continue
            p2=float(counts[k2])/total
            imp+=p1*p2
    return imp

#rows样本数据集
def entropy(rows):
    from math import log
    log2=lambda x:log(x)/log(2)
    results=uniquecounts(rows)
    # 此处开始计算熵的值
    ent=0.0
    for r in results.keys():
        p=float(results[r])/len(rows)
        ent=ent-p*log2(p)
    return ent

#II.4 统计某行中的所有取值
# 统计集合rows中每种分类的样本数目。（样本数据每一行数据的最后一列记录了分类结果）。rows样本数据
def uniquecounts(rows,index="null"):
    results={}
    for row in rows:
        # 目标结果在样本数据最后一列
        #r=row[len(row)-1]
        if index=="null":
            i = len(row)-1
        else:
            i = index
        r = row[i]
        if r not in results:
            results[r]=0
        results[r]+=1
    return results


#II.5 构建决策树，递归函数
# 构建决策树.scoref为信息增益的计算函数
def buildtree(rows,labels,scoref=giniimpurity):
    if len(rows)==0: return decisionnode()
    current_score=scoref(rows)

    # 定义一些变量以记录最佳拆分条件
    best_gain=0.0
    best_criteria=None
    best_sets=None

    column_count=len(rows[0])-1
    for col in range(0,column_count):    #遍历每一列（除最后一列，因为最后一列是目标结果）
        # 在当前列中生成一个由不同值构成的序列
        column_values={}
        for row in rows:
            column_values[row[col]]=1
        # 接下来根据这一列中的每个值，尝试对数据集进行拆分
        for value in column_values.keys():
            (set1,set2)=divideset(rows,col,value)

            # 计算信息增益
            p=float(len(set1))/len(rows)
            gain=current_score-p*scoref(set1)-(1-p)*scoref(set2)
            if gain>best_gain and len(set1)>0 and len(set2)>0:   #找到信息增益最大的分类属性
                best_gain=gain
                best_criteria=(col,value)
                best_sets=(set1,set2)
    # 创建子分支
    if best_gain>0:
        trueBranch=buildtree(best_sets[0],labels)   #创建分支
        falseBranch=buildtree(best_sets[1],labels)  #创建分支
        return decisionnode(col=best_criteria[0],colName=labels[best_criteria[0]],value=best_criteria[1],tb=trueBranch,fb=falseBranch)  #返回决策树节点
    else:
        return decisionnode(results=uniquecounts(rows))

#------------------------II.树的转化(特有)-----------------------------
#II.1 生成Json/字典树(特征取值写在分支上)
def DecisionnodeToJson(dataSet,tree,labels,text):
    #是分支节点，name是属性名，传给后代的两个text是value 和 not vavlue
    if tree.results==None:
        myTree={"name":str(labels[tree.col]),"col":tree.col,"text":text,"children":[{},{}]}
        myTree["children"][0]=DecisionnodeToJson(dataSet,tree.tb,labels,str(tree.value))
        #不是这个取值，应该是tree.col列的其他取值
        allVals = uniquecounts(dataSet,tree.col)
        allVals.pop(str(tree.value))
        otherVals=""
        for value in allVals: 
            otherVals += str(value)
            otherVals += ","
        #去除多余的" , "
        otherVals = otherVals[:-1]
        #print("---> tree.vlue:",tree.value,str(tree.value),"|",str(otherVals),"|",uniquecounts(dataSet,tree.col),"|",allVals)
        myTree["children"][1]=DecisionnodeToJson(dataSet,tree.fb,labels,otherVals)
    #是叶子节点，name 是分类结果
        return myTree
    else:
        txt=""
        for key in tree.results.keys():
            txt+=str(key)
        return {"name":txt,"col":"null","text":text,"children":"null"}

#II.2 JsonToDecisionnode辅助函数，根据列名确定列号
def nameToIndex(labels,name):
    for i in range(len(labels)):
        if name == labels[i]:
            return i
    return 0

#II.3 从字典树构建一个二叉树
def JsonToDecisionnode(jsonTree,root,labels):
    if root == None:
        root = decisionnode()
    #如果为叶子节点
    if jsonTree["children"] == "null":
        #root.col = nameToIndex(json["name"])
        dictResults = {}
        results = list(jsonTree["name"].split(","))#.rstrip().split(" , "))
        for value in results:
            dictResults[value]=1
        #print("dictResults:\n",dictResults)
        root.results = dictResults
    #如果是分支节点
    else:
        #root.col = nameToIndex(labels,jsonTree["name"])
        root.col = jsonTree["col"]
        root.colName = jsonTree["name"]
        #分支节点的value，看其true分支的text是什么即可
        root.value = jsonTree["children"][0]["text"]
        root.tb = JsonToDecisionnode(jsonTree["children"][0],root.tb,labels)
        root.fb = JsonToDecisionnode(jsonTree["children"][1],root.fb,labels)
    return root

#------------------------III.分类和评定------------------------------
def classify(jsonTree,observation,labels):
    #如果是叶子节点
    if jsonTree["children"]=="null":
        return jsonTree["name"]
    #是分支节点
    else:
        #找到本节点属性列对应的属性值
        v=observation[jsonTree['col']]#nameToIndex(jsonTree['name'],labels)]
        branch=None
        #如果这个值就是节点的子节点的分支上的引导文字
        if v==jsonTree["children"][0]["text"]:
            branch=jsonTree["children"][0]
        else:
            branch=jsonTree["children"][1]
        return classify(branch,observation,labels)

#检测精度，调用classify方法
def checkAccuracy(jsonTree,observations,labels):
    total = float(len(observations))
    if total <= 0:
        return 0    
    correct = 0.0
    classes = []
    #仅用于输出
    counts = 0
    for observation in observations:
        result = Classify(jsonTree,observation)
        classes.append(result)
        if str(result) == str(observation[-1]):
            correct += 1.0
        #仅用于输出
        if counts < 10:
            #print("line:",observation[:-1])
            #print("result: 真实:",observation[-1],"|预测:",result)
            counts += 1
    return correct/total,classes

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

#II.3 返回最多的类别名
def majorityCnt(classList):
    classCount={}
    for vote in classList:
        if vote not in classCount.keys(): classCount[vote] = 0
        classCount[vote] += 1
    return max(classCount, key=classCount.get)

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

            
def splitDataSet_dis(dataSet, axis, value):
    #print("----->",dataSet,axis,value)
    """
    输入：数据集，选择维度，选择值
    输出：划分数据集
    描述：按照给定特征划分数据集；去除选择维度中等于选择值的项
    """
    retDataSet = []
    falseDataSet = []
    for featVec in dataSet:
        #print("featVec----->>",featVec,"\naxis:",axis)
        if featVec[axis] == value:
            #reduceFeatVec = featVec[:axis]
            #reduceFeatVec.extend(featVec[axis+1:])
            retDataSet.append(featVec)
        else:
            #reduceFeatVec = featVec[:axis]
            #reduceFeatVec.extend(featVec[axis+1:])
            falseDataSet.append(featVec)
    return retDataSet,falseDataSet

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
        labelIndex = labels.index(featKey)
        #print("为何是10?????",labels,"\n",featKey,"\n",labels.index(featKey))
        #用于递归的子labels
        subLabels = labels[:] 
        '''
        if labelIndex != "null":
        print(labelIndex)
        print("->",labels)
        del(labels[labelIndex])          #del(labels[labelIndex])   删除本节点特征
        '''
        
        #0孩子，只有1个属性
        threshold = children[0]["text"]
        trueDataSet,falseDataSet = splitDataSet_dis(dataSet,labelIndex,threshold)
        trueTestSet,falseTestSet = splitDataSet_dis(testData,labelIndex,threshold)
        if len(trueDataSet) > 0 and len(trueTestSet) > 0:
            inputTree["children"][0] = pruningTree(children[0],trueDataSet,trueTestSet,subLabels,weight)
        
        if len(falseDataSet) > 0 and len(falseTestSet) > 0:
            inputTree["children"][1] = pruningTree(children[1],falseDataSet,falseTestSet,subLabels,weight)            

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
    

#--------------------------X.总控制函数()----------------------------#
#生成树，预测单条，预测多条，计算精度
#------------------------------------------------------------------#
#生成CART树
#输入:dataSource:{csv,db} sourceName:{csv,db.table} fields{}  target:{tree,json}
#输出:根据target输出tree,json
def GenerateCART(dataSource="db",sourceName="db_dataset.paly",fields=[],target="dictTree",pruning="none",outSourceName="db_slg.iri_test"):
    '''常用变量定义'''
    #数据集合(二维数组)
    sourceDataSet = []
    #数据表头/特征名(一维数组)
    labels = []
    #cart树
    cartTree = decisionnode()
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
        dataSet,labels = readFromCSV(sourceName)
    elif  dataSource == 'db':
        dbname = sourceName.split('.')[0]
        tablename = sourceName.split('.')[1]
        sourceDataSet,labels = readFromDB(dbname,tablename,fields)
        if pruning == "outpruning":
            outdbname = outSourceName.split('.')[0]
            outtablename = outSourceName.split('.')[1]
            outtestData,labels = readFromDB(outdbname,outtablename,fields) 
    else:        
        return {"message":"please specify the dataSource, csv or db" }

    '''树训练'''

    '''树剪枝/优化'''
    '''树训练,将循环5次找到最佳模型，三种剪枝模式由高层指定'''    
    #五次循环找最佳
    for i in range(5):        
        #内剪枝只有内部测试集精度
        #内部交叉验证剪枝,需要切分数据集,使用内部测试数据集合训练
        if pruning == "inpruning":
            dataSet,intestData = createCVDataSet(sourceDataSet,some_list=[0,1],probabilities=[1-SPLIT_PROP,SPLIT_PROP])
            #生成
            starttime = datetime.datetime.now()
            
            cartTree = buildtree(dataSet,labels)
            '''树转化统一接口'''
            dictTree = DecisionnodeToJson(dataSet,cartTree,labels,"null")
            
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
            
            cartTree = buildtree(dataSet,labels)
            '''树转化统一接口'''
            dictTree = DecisionnodeToJson(dataSet,cartTree,labels,"null")
            
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
            
            cartTree = buildtree(dataSet,labels)
            '''树转化统一接口'''
            dictTree = DecisionnodeToJson(dataSet,cartTree,labels,"null")
            
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
    if target == "dictTree":  
        print('-------------------------dictTree:----------------------------\n',DictTrees)
        return DictTrees[ACCIndex][:-1]
    elif target == "biTree":
        return cartTree
    elif target == "json":
        print('-------------------------json:----------------------------\n',DictTrees)        
        return json.dumps(DictTrees[ACCIndex][0]),DictTrees[ACCIndex][1],DictTrees[ACCIndex][2],DictTrees[ACCIndex][3]
    else:        
        return {"message":"please specify the target, dictTree，biTree or json"},datasize,costtime,trainACC

#根据生成好的CART树dictTree ,对新的观测数据observation进行分类
def Classify(dictTree,observation):
    return classify(dictTree,observation,[])

#根据生成好的CART树dictTree ,对新的观测数据集observations进行分类
def ClassifyAll(dictTree,observations):
    classes = []
    for observation in observations:
        classes.append(classify(dictTree,observation,[]))
    return classes


#测试精度(dictTree字典树,测试向量集(二维数组))
#返回精度和预测结果集合
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
    return checkAccuracy(dictTree,dataSet,[])

#数据库读取函数参考
#def readFromDB(dbname="db_dataset",tablename='paly',fields=[])

#---------------------------终端执行------------------------------
#只有在执行当前模块时才会运行
if __name__=='__main__':  
    '''
    #生成CART (数据源类型，数据源，参与生成的域名)
    dictTree = GenerateCART("db","db_dataset.personal_transcripts_discrete_cs",['English','CET4','CET6','AdvancedMath','LinearAlgebra','ProbabilityTheory','DataStructure','DataBase','ComputerNetwork','OperatingSystem','CompositionPrinciple','CppProgramming','ProgrammingPractice','JavaProgramming','CSorSE','NCRE_CPP2'],"dictTree")
    
    #dictTree = GenerateCART("db","db_dataset.forecast2",['四级','六级','政治面貌','计算机等级','综合能力','性别','result'],"dictTree")
    #进行单条预测(决策树，观测数据)
    print("--结果-->",Classify(dictTree,['failed', 'pass', 'failed', 'excellent', 'excellent', 'excellent', 'excellent', 'excellent', 'failed', 'excellent', 'failed', 'excellent', 'excellent', 'good', 'failed']))#结果:'pass'

    
    #进行多条预测检测精度(决策树,观测数据集合)
    accuracy = CheckAccuracy(dictTree,'db','db_dataset.personal_transcripts_discrete_cs',['English','CET4','CET6','AdvancedMath','LinearAlgebra','ProbabilityTheory','DataStructure','DataBase','ComputerNetwork','OperatingSystem','CompositionPrinciple','CppProgramming','ProgrammingPractice','JavaProgramming','CSorSE','NCRE_CPP2'])
    print('accuracy: {:.2%}'.format(accuracy))

    #print('accuracy: {:.2%}'.format(CheckAccuracy(dictTree,'db','db_dataset.forecast2',['四级','六级','政治面貌','计算机等级','综合能力','性别','result'])))
    '''
    
    fields=['English','CET4','CET6','AdvancedMath','LinearAlgebra','ProbabilityTheory','DataStructure','DataBase','OperatingSystem','CppProgramming','ProgrammingPractice','JavaProgramming','NCRE_CPP2']
    result = GenerateCART("db","db_dataset.15级计算机专业个人成绩离散化表_train",fields,"dictTree","none","db_dataset.15级计算机专业个人成绩离散化表_test")
    print(result)
    dictTree = result[0]
    print(CheckAccuracy(dictTree,dataSource="db",sourceName="db_dataset.15级计算机专业个人成绩离散化表_test",fields=fields))
   
   
