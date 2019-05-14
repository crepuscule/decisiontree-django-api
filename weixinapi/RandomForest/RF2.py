# Random Forest Algorithm on Sonar Dataset
from random import seed
from random import randrange
from csv import reader
from math import sqrt
import pymysql
import json

DBHOST = "47.95.196.25"
DBUSER = "root"
DBPWD = "12345678"

# Load a CSV file
# 从csv
def load_csv(filename):
   dataset = list()
   with open(filename, 'r') as file:
       csv_reader = reader(file)
       for row in csv_reader:
           if not row:
               continue
           dataset.append(row)
   return dataset

#!!!!----这里引入加载数据库文件的模块---!!!!!
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


# Convert string column to float
def str_column_to_float(dataset, column):
   for row in dataset:
       row[column] = float(row[column].strip())

# Convert string column to integer
def str_column_to_int(dataset, column):
   class_values = [row[column] for row in dataset]
   unique = set(class_values)
   lookup = dict()
   for i, value in enumerate(unique):
       lookup[value] = i
   for row in dataset:
       row[column] = lookup[row[column]]
   return lookup

# Split a dataset into k folds
def cross_validation_split(dataset, n_folds):
   dataset_split = list()
   dataset_copy = list(dataset)
   #print("----->",dataset_copy)
   fold_size = len(dataset) / n_folds
   for i in range(n_folds):
       fold = list()
       while len(fold) < fold_size:
           #print("->>",dataset_copy)
           if len(dataset_copy) == 0:
               break
           index = randrange(len(dataset_copy))
           fold.append(dataset_copy.pop(index))
       dataset_split.append(fold)
   return dataset_split

# Calculate accuracy percentage
def accuracy_metric(actual, predicted):
   correct = 0
   for i in range(len(actual)):
       if actual[i] == predicted[i]:
           correct += 1
   return correct / float(len(actual)) * 100.0

# Evaluate an algorithm using a cross validation split
def evaluate_algorithm(dataset, algorithm, n_folds, *args):
   folds = cross_validation_split(dataset, n_folds)
   scores = list()
   for fold in folds:
       train_set = list(folds)
       train_set.remove(fold)
       train_set = sum(train_set, [])
       test_set = list()
       for row in fold:
           row_copy = list(row)
           test_set.append(row_copy)
           row_copy[-1] = None
       predicted = algorithm(train_set, test_set, *args)
       actual = [row[-1] for row in fold]
       accuracy = accuracy_metric(actual, predicted)
       scores.append(accuracy)
   return scores

# Split a dataset based on an attribute and an attribute value
def test_split(index, value, dataset):
   left, right = list(), list()
   for row in dataset:
       if row[index] < value:
           left.append(row)
       else:
           right.append(row)
   return left, right

# Calculate the Gini index for a split dataset
def gini_index(groups, class_values):
   gini = 0.0
   for class_value in class_values:
       for group in groups:
           size = len(group)
           if size == 0:
               continue
           proportion = [row[-1] for row in group].count(class_value) / float(size)
           gini += (proportion * (1.0 - proportion))
   return gini

# Select the best split point for a dataset
def get_split(dataset, n_features):
   class_values = list(set(row[-1] for row in dataset))
   b_index, b_value, b_score, b_groups = 999, 999, 999, None
   features = list()
   while len(features) < n_features:
       index = randrange(len(dataset[0])-1)
       if index not in features:
           features.append(index)
   for index in features:
       for row in dataset:
           groups = test_split(index, row[index], dataset)
           gini = gini_index(groups, class_values)
           if gini < b_score:
               b_index, b_value, b_score, b_groups = index, row[index], gini, groups
   return {'index':b_index, 'value':b_value, 'groups':b_groups}

# Create a terminal node value
def to_terminal(group):
   outcomes = [row[-1] for row in group]
   return max(set(outcomes), key=outcomes.count)

# Create child splits for a node or make terminal
def split(node, max_depth, min_size, n_features, depth):
   left, right = node['groups']
   del(node['groups'])
   # check for a no split
   if not left or not right:
       node['left'] = node['right'] = to_terminal(left + right)
       return
   # check for max depth
   if depth >= max_depth:
       node['left'], node['right'] = to_terminal(left), to_terminal(right)
       return
   # process left child
   if len(left) <= min_size:
       node['left'] = to_terminal(left)
   else:
       node['left'] = get_split(left, n_features)
       split(node['left'], max_depth, min_size, n_features, depth+1)
   # process right child
   if len(right) <= min_size:
       node['right'] = to_terminal(right)
   else:
       node['right'] = get_split(right, n_features)
       split(node['right'], max_depth, min_size, n_features, depth+1)

# Build a decision tree
def build_tree(train, max_depth, min_size, n_features):
   root = get_split(dataset, n_features)
   split(root, max_depth, min_size, n_features, 1)
   return root

# Make a prediction with a decision tree
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

# Create a random subsample from the dataset with replacement
def subsample(dataset, ratio):
   sample = list()
   n_sample = round(len(dataset) * ratio)
   while len(sample) < n_sample:
       index = randrange(len(dataset))
       sample.append(dataset[index])
   return sample

# Make a prediction with a list of bagged trees
def bagging_predict(trees, row):
   predictions = [predict(tree, row) for tree in trees]
   return max(set(predictions), key=predictions.count)

# Random Forest Algorithm
def random_forest(train, test, max_depth, min_size, sample_size, n_trees, n_features):
   trees = list()
   for i in range(n_trees):
       sample = subsample(train, sample_size)
       tree = build_tree(sample, max_depth, min_size, n_features)
       trees.append(tree)
   predictions = [bagging_predict(trees, row) for row in test]
   return(predictions)

# Test the random forest algorithm
seed(1)
# load and prepare data
filename = 'ForRF_15级计算机专业个人成绩表_NCRE_CPP.csv'#'sonar.all-data.csv'
dataset = load_csv(filename)
# convert string attributes to integers
for i in range(0, len(dataset[0])-1):
   str_column_to_float(dataset, i)
# convert class column to integers
str_column_to_int(dataset, len(dataset[0])-1)
# evaluate algorithm
n_folds = 5
max_depth = 100
min_size = 1
sample_size = 1.0
n_features = int(sqrt(len(dataset[0])-1))
for n_trees in [1, 5, 10,15,20,25,30,35,40]:
   scores = evaluate_algorithm(dataset, random_forest, n_folds, max_depth, min_size, sample_size, n_trees, n_features)
   print('Trees: %d' % n_trees)
   print('Scores: %s' % scores)
   print('Mean Accuracy: %.3f%%' % (sum(scores)/float(len(scores))))
