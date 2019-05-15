from django.contrib import admin
from weixinapi.models import DataSet,Tree,Analysis

# Register your models here.

class DataSetAdmin(admin.ModelAdmin):
    list_display = ["dataSet_id","dataSet_name","dataSet_type",'data_type',"table_name","fields","size","create_time"]


class TreeAdmin(admin.ModelAdmin):
    list_display = ["tree_id","tree_name","dataSet_id",'outDataSet_id',"tree_type","data_type","optimize_type","depth","nodes_num",'datasize','costtime','trainacc','sample_ratio','feature_ratio',"create_time","fields"]


class AnalysisAdmin(admin.ModelAdmin):
    list_display = ["analysis_id","analysis_name","tree_id","dataSet_id","accuracy","ifthen","content","create_time"]

admin.site.register(DataSet,DataSetAdmin)
admin.site.register(Tree,TreeAdmin)
admin.site.register(Analysis,AnalysisAdmin)

