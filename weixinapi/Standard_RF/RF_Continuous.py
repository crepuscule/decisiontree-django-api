from random import seed
from random import randint
from csv import reader
import pdb
import re
import json
import pymysql
import operator
import copy
import datetime

DBHOST = "47.95.196.25"
DBUSER = "root"
DBPWD = "12345678"

#这里需要引入数据库读取方法，树字典转化器等

# 数据处理
'''导入数据'''
def load_csv(filename):
    dataset = list()
    with open(filename, 'r') as file:
        csv_reader = reader(file)
        for row in csv_reader:
            if not row:
                continue
            dataset.append(row)    
    return dataset[1:],dataset[0]

def readFromDB(dbname="db_slg",tablename='iris',fields=[]):
    print("``````````````````````RF_Continuous.py``````````````````````````\nin readFromDB() , use %s . %s " % (dbname,tablename), "\nfields:\n" ,fields)
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
          "\n--------------------------前10条dataSet:---------------------\n",dataSet[:5],len(dataSet),
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
  
'''划分训练数据与测试数据'''
def split_train_test(dataset, ratio=0.2):
    #ratio = 0.2  # 取百分之二十的数据当做测试数据
    num = len(dataset)
    train_num = int((1-ratio) * num)
    dataset_copy = list(dataset)
    traindata = list()
    while len(traindata) < train_num:
        index = randint(0,len(dataset_copy)-1)
        traindata.append(dataset_copy.pop(index))
    testdata = dataset_copy
    return traindata, testdata


'''试探分枝'''
def data_split(index, value, dataset):
    left, right = list(), list()
    #只适合于连续值，不适用于离散值
    for row in dataset:
        if row[index] < value:
            left.append(row)
        else:
            right.append(row)
    return left, right

'''计算基尼指数'''
def calc_gini(groups, class_values):
    gini = 0.0
    total_size = 0
    for group in groups:
        total_size += len(group)
    for group in groups:
        size = len(group)
        if size == 0:
            continue
        for class_value in class_values:
            proportion = [row[-1] for row in group].count(class_value) / float(size)
            gini += (size / float(total_size)) * (proportion * (1.0 - proportion))
    return gini

'''找最佳分叉点'''
def get_split(dataset, n_features):
    class_values = list(set(row[-1] for row in dataset))
    b_index, b_value, b_score, b_groups = 999, 999, 999, None
    features = list()
    #限制特征的数量，这些特征随机取放到列表中
    while len(features) < n_features:
        index = randint(0, len(dataset[0]) - 2)  # 往features添加n_features个特征（n_feature等于特征数的根号），特征索引从dataset中随机取
        if index not in features:
            features.append(index)
    #遍历随机取出的特征，尝试寻找最佳切分点
    for index in features:
        for row in dataset:
            groups = data_split(index, row[index], dataset)
            gini = calc_gini(groups, class_values)
            if gini < b_score:
                b_index, b_value, b_score, b_groups = index, row[index], gini, groups
    return {'index': b_index, 'value': b_value, 'groups': b_groups}  # 每个节点由字典组成

'''多数表决'''
# 叶子节点的类别标签
def to_terminal(group):
    outcomes = [row[-1] for row in group]
    return max(set(outcomes), key=outcomes.count)

'''分枝'''
def split(node, max_depth, min_size, n_features, depth):
    #节点中的groups分为左右两支，前小后大
    left, right = node['groups']
    del (node['groups'])
    #如果有一边是空的，那么就是传入的node就是叶子节点，类别是纯的
    if not left or not right:
        node['left'] = node['right'] = to_terminal(left + right)  # 叶节点不好理解
        return
    
    #类似剪枝，这里约束深度
    if depth >= max_depth:
        node['left'], node['right'] = to_terminal(left), to_terminal(right)
        return
    
    #约束最小节点数据集，小于这个数据集直接变为叶子节点
    if len(left) <= min_size:
        node['left'] = to_terminal(left)
    else:
        node['left'] = get_split(left, n_features)
        split(node['left'], max_depth, min_size, n_features, depth + 1)
        
    if len(right) <= min_size:
        node['right'] = to_terminal(right)
    else:
        node['right'] = get_split(right, n_features)
        split(node['right'], max_depth, min_size, n_features, depth + 1)

'''建立一棵树'''
def build_one_tree(train, max_depth, min_size, n_features):
    root = get_split(train, n_features)
    split(root, max_depth, min_size, n_features, 1)
    return root

'''用一棵树来预测'''
def predict(node, row):
    if row[node['index']] < node['value']:
        if isinstance(node['left'], dict):
            return predict(node['left'], row)
        else:
            return node['left']
    else:
        if isinstance(node['right'], dict):
            return predict(node['right'], row)
        else:
            return node['right']


#-----------------------------X. 总控制类-------------------------------------
# 随机森林类
class RandomForest:    
    # 森林 树数目（几个数据集），最大树深度（约束时间，过拟合等），停止的分枝样本最小数目，交叉验证采集训练数据集和测试数据集比例，特征采样（每棵树的特征多少）
    def __init__(self,trees_num, max_depth, leaf_min_size, sample_ratio, feature_ratio):
        self.trees_num = trees_num                # 森林的树的数目
        self.max_depth = max_depth                # 树最深深度
        self.real_depth = 0                       # 森林真实最深深度
        self.leaf_min_size = leaf_min_size        # 建立树时，停止的分枝样本最小数目
        self.samples_split_ratio = sample_ratio   # 采样，创建子集的比例（行采样）
        self.feature_ratio = feature_ratio        # 特征比例（列采样）
        self.trees = list()                       # 森林
        self.dataset = []
        self.labels = []
        self.costtime = 0.0                       #森林构建花费时间
        self.trainacc = 0.0
        
    #--------------------------数据集-----------------------------
    def loadDataSet(self,sourceType,splitType,fields,sourceName):
        #先导入数据集合,不使用内部的交叉验证，使用外界的自行验证
        if sourceType == 'csv':        
            self.dataset,self.labels = load_csv(sourceName)
        else:
            dbname = sourceName.split('.')[0]
            tablename = sourceName.split('.')[1]
            self.dataset,self.labels = readFromDB(dbname,tablename,fields)
            
            
        print("---load data compete:--->\n",self.labels,'\n',self.dataset[0],len(self.dataset))
        ''' 使用内部测试集
        #outDataSet,labels = load_csv('iri_test.csv')
        #print("->",outDataSet,len(outDataSet))        
        import time
        seed(time.time())   #每一次执行本文件时都能产生同一个随机数
        traindata,testdata = split_train_test(dataset, ratio=0.2)
        '''
        
    '''有放回的采样，创建数据子集,类内外均可用'''
    #抽出总体数据集合的samples_split_ratio * len(dataSet)条数据
    def sample_split(self, dataset):
        import time
        seed(time.time())
        sample = list()
        n_sample = round(len(dataset) * self.samples_split_ratio)
        while len(sample) < n_sample:
            #随机抽取，但是放回
            index = randint(0, len(dataset) - 2)
            sample.append(dataset[index])
        return sample
        
    #------------------------------森林的生成----------------------------
    '''建立随机森林,可以选择返回目标,同时返回训练集的精确度'''
    def build_RandomForest(self,target):
        #类数据适应
        train = self.dataset
        labels = self.labels
        #--------------------        
        max_depth = self.max_depth
        min_size = self.leaf_min_size
        n_trees = self.trees_num
        #列采样，从M个feature中，选择m个(m<<M),即选择n_features个特征
        n_features = int(self.feature_ratio * (len(train[0])-1))
        
        print("随机森林构建中...")
        starttime = datetime.datetime.now()
        #创建n_trees棵树
        for i in range(n_trees):
            #有放回的随机抽样，每次都即抽即训练
            sample = self.sample_split(train)
            #抽完立马进行训练
            tree = build_one_tree(sample, max_depth, min_size, n_features)
            self.trees.append(tree)
        endtime = datetime.datetime.now()
        self.costtime = (endtime - starttime).total_seconds()*1000
        #注意：因为树太多，转化效率太低，只在需要展示的时候再转化为JSON 所以在utils中编写单独的方法用于在展示随机森林时转化为可绘画的JSON
        #先完善字典森林，重置该森林:
        self.trees = self.toJsons(self.trees,labels)
        self.trainacc,result = self.accuracy_metric(self.trees,'list',train)
        if target=="dictTree":
            return self.trees
        else:
            return json.dumps(self.trees)
    
    def toJsons(self,trees,labels):
        jsons = []
        def toJson(tree,depth):
            #只要不是叶子就递归
            if isinstance(tree['left'],dict):
                toJson(tree['left'],depth+1)
            if isinstance(tree['right'],dict):
                toJson(tree['right'],depth+1)
            #添加一个name属性，这就是所有需要做的
            tree['name'] = labels[tree['index']]
            #记录最深深度
            if depth > self.real_depth:
                self.real_depth = depth
            return tree
        
        for tree in trees:
            jsons.append(toJson(tree,1))
        
        return jsons
    
    def getProperties(self):
        data_type = 'Continuous'
        nodes_num = self.trees_num
        depth = self.real_depth
        datasize = len(self.dataset)
        costtime = self.costtime
        trainacc = self.trainacc
        return data_type,nodes_num,depth,datasize,costtime,trainacc
    #--------------------------分类与测试-------------------------------
    '''随机森林预测的多数表决'''
    @staticmethod
    def bagging_predict(trees,onetestdata):
        predictions = [predict(tree, onetestdata) for tree in trees]
        preDict = {}
        for x in predictions:
            if x not in preDict:
                preDict[x] = 1
            else:
                preDict[x] += 1
        #print(preDict,max(set(predictions), key=predictions.count))
        return max(set(predictions), key=predictions.count)

    '''计算建立的森林的精确度'''
    @staticmethod
    def accuracy_metric(trees,sourceType,sourceName,fields=[]):
        if sourceType == 'list':
            testdata = sourceName
        elif sourceType == 'db':
            dbname = sourceName.split('.')[0]
            tablename = sourceName.split('.')[1]
            testdata,labels = readFromDB(dbname,tablename,fields)
        elif sourceType == 'csv':
            testdata,labels = load_csv(sourceName)     
        #-----------------------------
        correct = 0
        predicteds = []
        for i in range(len(testdata)):
            predicted = RandomForest.bagging_predict(trees,testdata[i])
            predicteds.append(predicted)
            #print(testdata[i][-1])
            if testdata[i][-1] == predicted:
                correct += 1
        return correct / float(len(testdata)),predicteds




# 测试
if __name__ == '__main__':
    trees_num = 1000
    max_depth = 30 #调参（自己修改） #决策树深度不能太深，不然容易导致过拟合
    min_size = 1
    sample_ratio = 0.3
    feature_ratio=0.4#0.3
    
    fields=['English','CET4','CET6','AdvancedMath','LinearAlgebra','ProbabilityTheory','DataStructure','DataBase','OperatingSystem','CppProgramming','ProgrammingPractice','JavaProgramming','NCRE_CPP2']
    
    '''建立森林三连'''
    #1 实例化一个对象,指定参数
    myRF = RandomForest(trees_num, max_depth, min_size, sample_ratio, feature_ratio)
    #2 填入数据集合,放入对象中
    myRF.loadDataSet(sourceType='db',splitType='in',fields=fields,sourceName='db_dataset.15级计算机专业个人成绩表_train')
    #pdb.set_trace()
    #3 生成随机森林
    randomForest = myRF.build_RandomForest("json")
    data_type,nodes_num,depth,datasize,costtime,trainacc = myRF.getProperties()
    print(data_type,nodes_num,depth,datasize,costtime,trainacc)
    '''执行预测和测试精度'''
    testacc = RandomForest.accuracy_metric(json.loads(randomForest),sourceType='db',fields=fields,sourceName='db_dataset.15级计算机专业个人成绩表_test')
    print('随机森林,训练集准确率：\n','\n',trainacc)
    print('外部测试集准确率：',testacc)
