from weixinapi import models
DBNAME = "db_dataset."


#partDictTree['dataSet_id'] = {decisionTreeType,nodes_num,depth,datasize,costtime,trainACC}
class TreeGenerator:
    def __init__(self):
        pass
    def Generate(self,partDictTree):
        try:
            dataSet = models.DataSet.objects.get(pk=partDictTree['dataSet_id'])
            if partDictTree['optimize_type'] == "outpruning":
                outDataSet = models.DataSet.objects.get(pk=partDictTree['outDataSet_id'])
                outDataSetName = outDataSet.table_name
            else:
                outDataSetName = ''
        except:
            return {'message':'dataset not found'}
        
        #这里将fields字符串化为list
        if partDictTree['fields']=="":
            partDictTree['fields'] = []
        else:
            fields=partDictTree['fields'].split(',')
            partDictTree['fields']=fields            
        print(partDictTree['fields'])
        
        if partDictTree['optimize_type'] == "outpruning":
            if dataSet.fields !=  outDataSet.fields:
                return {'message':'outDataset\'fields is not match to DataSet\'s'}
        
        
        if partDictTree['optimize_type'] == 'RandomForest':
            from weixinapi.Standard_RF import RF_Standard
            RF_controller = RF_Standard.RF('db',DBNAME+dataSet.table_name,partDictTree['fields'])
            partDictTree['tree_dict'] = RF_controller.GenerateRF(partDictTree['nodes_num'],partDictTree['depth'],partDictTree['sample_ratio'],partDictTree['feature_ratio'],'json') 
            partDictTree['data_type'],partDictTree['nodes_num'],partDictTree['depth'],partDictTree['datasize'],partDictTree['costtime'],partDictTree['trainACC']=RF_controller.GetProperties()
            return partDictTree
            
        #再根据类型判断调用哪个模块
        # CART
        if partDictTree['tree_type'] == 'CART':
            #try:
            from weixinapi.Standard_CART import CART_Standard
            CART_controller = CART_Standard.CART('db',DBNAME+dataSet.table_name,partDictTree['fields'])
            partDictTree['tree_dict'] = CART_controller.GenerateCART('json',partDictTree['optimize_type'],partDictTree['pruning_weight'],DBNAME+outDataSetName) 
            partDictTree['data_type'],partDictTree['nodes_num'],partDictTree['depth'],partDictTree['datasize'],partDictTree['costtime'],partDictTree['trainACC']=CART_controller.CalcProperties()
            #except Exception as e:
            #    print("in utils/TreeGenerator:",e)
            #    return  {'message':'can not build CART'} 
        #C4.5
        elif partDictTree['tree_type'] == 'C45':
            #try:
            from weixinapi.Standard_C45 import C45_Standard
            #注意 C45未开发数据库读取接口
            C45_controller = C45_Standard.C45('db',DBNAME+dataSet.table_name,partDictTree['fields'])
            partDictTree['tree_dict'] = C45_controller.GenerateC45('json',partDictTree['optimize_type'],partDictTree['pruning_weight'],DBNAME+outDataSetName) 
            partDictTree['data_type'],partDictTree['nodes_num'],partDictTree['depth'],partDictTree['datasize'],partDictTree['costtime'],partDictTree['trainACC']=C45_controller.CalcProperties()
            #except Exception as e:
            #    print("in utils/TreeGenerator:",e)
            #    return {'message':'can not build C4.5'} 
        #未指明方法
        else:
            return  {'message':'please specify the tree type'}
        return partDictTree

