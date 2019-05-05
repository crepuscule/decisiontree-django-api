'''AnalysisGenerator.py'''
DBNAME = "db_dataset."

from weixinapi import models
import json

class AnalysisGenerator:
    def __init__(self):
        pass
    #单条预测
    def Classify(self,partDictAnalysis):
        #Classify(dictTree,observation,decisionTreeType):   CART
        #Classify(dictTree,labels,observation,decisionTreeType): C45
        '''数据读取'''
        #先读取dictTree
        try:
            tree = models.Tree.objects.get(pk=partDictAnalysis['tree_id'])
        except:
            return {'message':'tree not found'}
        #再取出需要做分类的相关参数
        dictTree = json.loads(tree.tree_dict)
        fields = tree.fields.split(',')
        #(在单条数据中dataSet_id用作单条数据的存储位置,上层已经验证过其有数据，不用验证为空)
        observation = partDictAnalysis['dataSet_id'].split(',')
        decisionTreeType = tree.data_type

        '''执行分类'''
        #再根据类型判断调用哪个模块
        # CART
        if tree.tree_type == 'CART':
            #try:
            from weixinapi.Standard_CART import CART_Standard
            return CART_Standard.CART.Classify(dictTree,observation,decisionTreeType)
            #except Exception as e:
            #    print("in utils/AnalysisGenerator:",e)
            #    return  {'message':'can not build CART'} 
        #C4.5(由于算法实现原因，需要labels辅助进行分类)
        elif tree.tree_type == 'C45':
            #try:
            from weixinapi.Standard_C45 import C45_Standard
            return C45_Standard.C45.Classify(dictTree,fields,observation,decisionTreeType)
            #except Exception as e:
            #    print("in utils/TreeGenerator:",e)
            #    return {'message':'can not build C4.5'} 
        #未指明方法
        else:
            return  {'message':'please specify the tree type'}



    #测试集预测和分析
    def Generate(self,partDictAnalysis):
        #ClassifyAndAnalysis(dcitTree,dataSource='db',sourceName="db_dataset.lenses_one",fields=[],decisionTreeType):
        '''参数读取'''
        #先读取测试集合
        try:
            testDataSet = models.DataSet.objects.get(pk=partDictAnalysis['dataSet_id'])
        except:
            return {'message':'testdataset not found'}
        #再读取树
        try:
            tree = models.Tree.objects.get(pk=partDictAnalysis['tree_id'])
        except:
            return {'message':'tree not found'}        
        #再取出需要做分类的相关参数
        dictTree = json.loads(tree.tree_dict)
        fields = tree.fields.split(',')
        #(在单条数据中dataSet_id用作单条数据的存储位置,上层已经验证过其有数据，不用验证为空)
        sourceName = DBNAME+testDataSet.table_name
        decisionTreeType = tree.data_type

        #再根据类型判断调用哪个模块
        # CART
        if tree.tree_type == 'CART':
            #try:
            from weixinapi.Standard_CART import CART_Standard
            partDictAnalysis['accuracy'],partDictAnalysis['content'] = CART_Standard.CART.ClassifyAndAnalysis(dictTree,'db',sourceName,fields,decisionTreeType)
            partDictAnalysis['ifthen'] = CART_Standard.CART.GenerateIfThen(dictTree,decisionTreeType)
            partDictAnalysis['content']=','.join(partDictAnalysis['content'])
            #except Exception as e:
            #    print("in utils/TreeGenerator:",e)
            #    return  {'message':'can not build CART'} 
        #C4.5
        elif tree.tree_type == 'C45':
            #try:
            from weixinapi.Standard_C45 import C45_Standard
            partDictAnalysis['accuracy'],partDictAnalysis['content'] = C45_Standard.C45.ClassifyAndAnalysis(dictTree,'db',sourceName,fields,decisionTreeType)
            partDictAnalysis['ifthen'] = C45_Standard.C45.GenerateIfThen(dictTree,decisionTreeType)
            partDictAnalysis['content']=','.join(partDictAnalysis['content'])
            #except Exception as e:
            #    print("in utils/TreeGenerator:",e)
            #    return {'message':'can not build C4.5'} 
        #未指明方法
        else:
            return  {'message':'please specify the tree type'}
        return partDictAnalysis

