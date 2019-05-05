from django.db import models
from django.utils import timezone


class DataSet(models.Model):
    dataSet_id = models.AutoField(primary_key=True)
    dataSet_name = models.CharField(max_length= 200)
    dataSet_type = models.CharField(max_length= 200)
    table_name = models.CharField(max_length= 200)
    fields = models.TextField(default="")
    size = models.IntegerField(default=0)
    create_time = models.DateTimeField('cretetime',default=timezone.now)
     
class Tree(models.Model):
    tree_id = models.AutoField(primary_key=True)
    #dataSet_id = models.IntegerField(blank=False,null=False)
    dataSet = models.ForeignKey(DataSet,on_delete=models.PROTECT)
    tree_name = models.CharField(max_length= 200)
    tree_type = models.CharField(max_length= 200)
    data_type = models.CharField(max_length= 200,default="")
    optimize_type = models.CharField(max_length= 200,null=True)
    tree_dict = models.TextField(default="")
    fields = models.TextField(default="")
    depth = models.IntegerField(default=0)
    nodes_num = models.IntegerField(default=0)    
    create_time = models.DateTimeField('cretetime',default=timezone.now)
 
class Analysis(models.Model):
    analysis_id = models.AutoField(primary_key=True)
    #tree_id = models.IntegerField(blank=False,null=False)
    tree = models.ForeignKey(Tree,on_delete=models.PROTECT)
    #dataSet_id = models.IntegerField(blank=False,null=False)
    dataSet = models.ForeignKey(DataSet,on_delete=models.PROTECT)
    analysis_name = models.CharField(max_length= 200)
    accuracy = models.FloatField(default=0.0)
    ifthen = models.TextField(default="")
    content = models.TextField(null=True)
    create_time = models.DateTimeField('cretetime',default=timezone.now)
