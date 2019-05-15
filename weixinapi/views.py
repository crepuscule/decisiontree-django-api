#basic
import sys
import os
import json
import traceback
from django.shortcuts import render
from django.template import loader
from django.http import HttpResponse,JsonResponse
from . import models
#from django.http import QueryDict
#from django.views.decorators.csrf import csrf_protect

#rest_framework
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
from weixinapi.utils.serializers import DataSetSerializer
from weixinapi.utils.serializers import TreeSerializer
from weixinapi.utils.serializers import AnalysisSerializer

#others





# Create your views here.
def index(request,tree_id):
    pass

def uploadtrain(request):
    return render(request,'weixinapi/uploadtrain.html')

def uploadtest(request):
    return render(request,'weixinapi/uploadtest.html')

def dataSet(request,dataset_id):
    # [GET]dataset/id
    if request.method == "GET":
        try:
            if dataset_id == '':
                dataSet = models.DataSet.objects.all()
                serializer = DataSetSerializer(dataSet,many=True)
            else:
                dataSet = models.DataSet.objects.get(pk=dataset_id)
                serializer = DataSetSerializer(dataSet)
        except:            
            return JsonResponse({'message':'未找到相关资源'},status=404)
        return JsonResponse(serializer.data,safe=False)

    # [PUT]dataset/
    elif request.method == "PUT":
        data = JSONParser().parse(request)
        dataSet = None
        serializer = DataSetSerializer(dataSet,data=data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data)
        return JsonResponse(serializer.errors,status=400)

    # [POST]dataset/
    elif request.method == "POST":
        dataSet_name=request.POST.get('dataSet_name','dataset')
        dataSet_type=request.POST.get('dataSet_type','trainset')
        data_type = request.POST.get('data_type','Continuous')
        myFile = request.FILES.get('csvdataset')
        if not myFile:
            #return JsonResponse({'message':'no file uploaded'})
            return render(request,"weixinapi/failed.html")
        else:
            destination = open(os.path.join('weixinapi/uploads',myFile.name),'wb')
            for chunk in myFile.chunks():
                destination.write(chunk)
            destination.close()
            #开始调用模块转移数据到数据库
            #try:
            from weixinapi.utils import csv2Db
            table_name,size,fields = csv2Db.writeToDB('weixinapi/uploads/',myFile.name)
            newdataSet = models.DataSet(dataSet_name=dataSet_name,
                                        dataSet_type=dataSet_type,
                                        data_type = data_type,
                                        table_name=table_name,
                                        fields=','.join(fields),
                                        size=size)
            newdataSet.save()
            #except Exception as e:
            #    print("in [POST]dataset/ :" , e)
            #    return JsonResponse({'message':'can not upload to DB'})
            #return JsonResponse(DataSetSerializer(newdataSet).data)
            return render(request,"weixinapi/success.html")

    # [DELETE]dataset/id
    elif request.method == 'DELETE':
        try:
            dataSet = models.DataSet.objects.get(pk=dataset_id)
        except:
            return JsonResponse({'message':'未找到需要删除资源'},status=404)
        try:
            dataSet.delete()
        except:
            return JsonResponse({'message':'无法删除,该数据集正被其他对象使用'},status=409)
        return JsonResponse({'message':'删除成功'},status=200)
    else:
        return JsonResponse({'message':'不支持的方法','method':request.method},status=405)

        
def tree(request,tree_id):
    #GET请求用于获取tree
    if request.method == "GET":
        try:
            if tree_id == '':
                tree = models.Tree.objects.all()
                serializer = TreeSerializer(tree,many=True)
            else:
                tree = models.Tree.objects.get(pk=tree_id)
                serializer = TreeSerializer(tree)
        except:            
            return JsonResponse({'message':'未找到相关资源'},status=404)
        return JsonResponse(serializer.data,safe=False)
    #PUT请求用于客户端生成好的tree直接插入数据库
    elif request.method == "PUT":
        data = JSONParser().parse(request)
        tree = None
        serializer = TreeSerializer(tree,data=data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data)
        return JsonResponse(serializer.errors,status=400)
    #POST请求用于客户端传入训练集和类型在服务器端训练再插入数据库
    elif request.method == "POST":
        from weixinapi.utils.TreeGenerator import TreeGenerator
        treeGenerator = TreeGenerator()
        print(request)
        print("----------------------------")
        print(request.POST)
        newDictTree = treeGenerator.Generate(json.loads(request.POST.get('tree')))
        #如果调用中出现了问题，直接返回给客户端
        if 'message' in newDictTree.keys():
            return JsonResponse(newDictTree)
        #如果外部datasetid未定义，则使用datasetid替代
        if 'outDataSet_id' not in newDictTree.keys():
            newDictTree['outDataSet_id'] = newDictTree['dataSet_id'] 
        if 'sample_ratio' not in newDictTree.keys():
            newDictTree['sample_ratio']=0.0
        if 'feature_ratio' not in newDictTree.keys():
            newDictTree['feature_ratio'] = 0.0
        newTree = models.Tree(tree_name=newDictTree['tree_name'],
                              tree_type=newDictTree['tree_type'],
                              data_type=newDictTree['data_type'],
                              optimize_type=newDictTree['optimize_type'],
                              tree_dict=newDictTree['tree_dict'],
                              fields = ','.join(newDictTree['fields']),
                              depth=newDictTree['depth'],
                              nodes_num=newDictTree['nodes_num'],
                              datasize = newDictTree['datasize'],
                              costtime = newDictTree['costtime'],
                              trainacc = newDictTree['trainACC'],
                              sample_ratio = newDictTree['sample_ratio'],
                              feature_ratio = newDictTree['feature_ratio'],
                              dataSet_id=newDictTree['dataSet_id'],
                              outDataSet_id=newDictTree['outDataSet_id']
                              )
        newTree.save()
        #返回新创建对象的序列化JSON
        #return JsonResponse(TreeSerializer(newTree).data)
        return JsonResponse({"message":"决策树生成成功,请至决策树管理查看!"},status=200)

    elif request.method == 'DELETE':
        try:
            tree = models.Tree.objects.get(pk=tree_id)
        except:
            return JsonResponse({'message':'未找到相关资源'},status=404)
        try:
            tree.delete()
        except:
            return JsonResponse({'message':'无法删除,该决策树正被其他对象使用'},status=409)
        return JsonResponse({'message':'删除成功'},status=200)
    else:
        return JsonResponse({'message':'不支持的方法','method':request.method})



def analysis(request,analysis_id):
    if request.method == "GET":
        try:
            if analysis_id == '':
                analysis = models.Analysis.objects.all()
                serializer = AnalysisSerializer(analysis,many=True)
            else:
                analysis = models.Analysis.objects.get(pk=analysis_id)
                serializer = AnalysisSerializer(analysis)
        except:            
            return JsonResponse({'message':'未找到相关资源'},status=404)
        return JsonResponse(serializer.data,safe=False)
    elif request.method == "PUT":
        data = JSONParser().parse(request)
        analysis = None
        serializer = AnalysisSerializer(analysis,data=data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data)
        return JsonResponse(serializer.errors,status=400)
    elif request.method == "POST":
        partDictAnalysis = json.loads(request.POST.get('analysis'))
        #如果传输或者数据源头没有定义该值，只能返回
        if ("dataSet_id" not in partDictAnalysis) or (partDictAnalysis["dataSet_id"] == ""):
            return JsonResponse({'message':'Analysis\'dataSet_id is not defined'})
        #如果是数字，说明要生成分析报告
        elif str(partDictAnalysis["dataSet_id"]).isdigit():
            from weixinapi.utils.AnalysisGenerator import AnalysisGenerator
            analysisGenerator = AnalysisGenerator()
            newDictAnalysis = analysisGenerator.Generate(partDictAnalysis)
            newAnalysis = models.Analysis(tree_id=partDictAnalysis["tree_id"],
                                          dataSet_id=partDictAnalysis["dataSet_id"],
                                          analysis_name=partDictAnalysis["analysis_name"],
                                          accuracy=partDictAnalysis["accuracy"],
                                          ifthen=partDictAnalysis["ifthen"],
                                          content=partDictAnalysis["content"])
            newAnalysis.save()
            #return JsonResponse(AnalysisSerializer(newAnalysis).data)
            return JsonResponse({"message":"分析报告生成成功,请至分析报告管理查看"})
        #那么就是有单条预测值了
        else:
            from weixinapi.utils.AnalysisGenerator import AnalysisGenerator
            analysisGenerator = AnalysisGenerator()
            #只需要1个treeId和1个DataSet_id(向量而已)
            classResult = analysisGenerator.Classify(partDictAnalysis)
            return JsonResponse({"classResult":classResult},status=200)
        
    elif request.method == 'DELETE':
        try:
            analysis = models.Analysis.objects.get(pk=analysis_id)
        except:
            return JsonResponse({'message':'未找到相关资源'},status=404)
        try:
            analysis.delete()
        except:
            return JsonResponse({'message':'无法删除,该分析报告正被其他对象使用'},status=409)
        return JsonResponse({'message':'删除成功'},status=200)
    else:
        return JsonResponse({'message':'unsuported method','method':request.method},status=405)

def treeGraph(request):
    #GET请求获取一串JSON来构建树
    if request.method == "GET":
        #if request.GET.has_key('tree_id'):
        if 'tree_id' in request.GET:
            tree_id = request.GET.get('tree_id')
            tree = models.Tree.objects.get(pk=request.GET['tree_id'])
            print(tree.tree_dict)
            context = {'jsonContent': tree.tree_dict}
        #elif request.GET.has_key("json"):
        elif 'json' in request.GET:
            jsoncontent = request.GET.get('json')
            print(json)
            context = {'jsonContent': tree.tree_dict}
        else:
            return JsonResponse({"message":"必须指定树的tree_id或者json来绘制树图"})
        return render(request,'weixinapi/treeGraph.html',context)
    #POST请求则通过传输树的ID从数据库中读取获得
    elif request.method == "POST":
        tree = models.Tree.objects.get(pk=request.POST['tree_id'])
        print(tree.tree_dict)
        context = {'jsonContent': tree.tree_dict}
        return render(request,'weixinapi/treeGraph.html',context)
    else:
        return JsonResponse({"message":"不支持除get/post之外的请求"})


