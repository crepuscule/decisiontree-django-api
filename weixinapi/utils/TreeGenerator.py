from weixinapi import models
DBNAME = "db_dataset."

class TreeGenerator:
    def __init__(self):
        pass
    def Generate(self,partDictTree):
        try:
            dataSet = models.DataSet.objects.get(pk=partDictTree['dataSet_id'])
        except:
            return {'message':'dataset not found'}
        
        #这里将fields字符串化为list
        if partDictTree['fields']=="":
            partDictTree['fields'] = []
        else:
            fields=partDictTree['fields'].split(',')
            partDictTree['fields']=fields
        print(partDictTree['fields'])
        
        #再根据类型判断调用哪个模块
        # CART
        if partDictTree['tree_type'] == 'CART':
            #try:
            from weixinapi.Standard_CART import CART_Standard
            CART_controller = CART_Standard.CART('db',DBNAME+dataSet.table_name,partDictTree['fields'])
            partDictTree['tree_dict'] = CART_controller.GenerateCART('json') 
            partDictTree['data_type'],partDictTree['nodes_num'],partDictTree['depth']=CART_controller.CalcProperties()
            #except Exception as e:
            #    print("in utils/TreeGenerator:",e)
            #    return  {'message':'can not build CART'} 
        #C4.5
        elif partDictTree['tree_type'] == 'C45':
            #try:
            from weixinapi.Standard_C45 import C45_Standard
            #注意 C45未开发数据库读取接口
            C45_controller = C45_Standard.C45('db',DBNAME+dataSet.table_name,partDictTree['fields'])
            partDictTree['tree_dict'] = C45_controller.GenerateC45('json') 
            partDictTree['data_type'],partDictTree['nodes_num'],partDictTree['depth']=C45_controller.CalcProperties()
            #except Exception as e:
            #    print("in utils/TreeGenerator:",e)
            #    return {'message':'can not build C4.5'} 
        #未指明方法
        else:
            return  {'message':'please specify the tree type'}
        return partDictTree
