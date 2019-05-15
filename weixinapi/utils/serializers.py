from rest_framework import serializers
from weixinapi.models import DataSet
from weixinapi.models import Tree
from weixinapi.models import Analysis

class DataSetSerializer(serializers.Serializer): 
    dataSet_id = serializers.IntegerField(read_only=True)
    dataSet_name = serializers.CharField(required=True, allow_blank=False, max_length=200)
    dataSet_type = serializers.CharField(required=True, allow_blank=False, max_length=200)
    data_type = serializers.CharField(required=True, allow_blank=False, max_length=200)
    table_name = serializers.CharField(required=True, allow_blank=False)
    fields = serializers.CharField(required=True, allow_blank=False)
    size = serializers.IntegerField(required=True)
    create_time = serializers.DateTimeField(read_only=True,format='%Y-%m-%d %H:%M')
    def create(self, validated_data):
        return DataSet.objects.create(**validated_data)

class TreeSerializer(serializers.Serializer): 
    tree_id = serializers.IntegerField(read_only=True)
    tree_name = serializers.CharField(required=True, allow_blank=False, max_length=200)
    tree_type = serializers.CharField(required=True, allow_blank=False, max_length=200)
    data_type = serializers.CharField(required=True, allow_blank=False, max_length=200)
    optimize_type = serializers.CharField(required=False, allow_blank=True, max_length=200)
    tree_dict = serializers.CharField(required=True, allow_blank=False)
    fields = serializers.CharField(required=True, allow_blank=False)
    #对rf而言，传进来是最深深度约束，传出去是真实最深深度
    depth = serializers.IntegerField(required=True)
    nodes_num = serializers.IntegerField(required=True)
    #new
    datasize = serializers.IntegerField(required=True)
    costtime = serializers.FloatField(required=True)
    trainacc = serializers.FloatField(required=True)
    #RF
    sample_ratio = serializers.FloatField(required=True)
    feature_ratio = serializers.FloatField(required=True)
    create_time = serializers.DateTimeField(read_only=True,format='%Y-%m-%d %H:%M')
    dataSet_id = serializers.IntegerField(required=True)
    outDataSet_id = serializers.IntegerField(required=True)
    def create(self, validated_data):
        return Tree.objects.create(**validated_data)

class AnalysisSerializer(serializers.Serializer): 
    analysis_id = serializers.IntegerField(read_only=True)
    analysis_name = serializers.CharField(required=True, allow_blank=False, max_length=200)
    accuracy = serializers.FloatField(required=True)
    ifthen = serializers.CharField(required=True, allow_blank=False)
    content = serializers.CharField(required=False, allow_blank=True)
    create_time = serializers.DateTimeField(read_only=True,format='%Y-%m-%d %H:%M')
    dataSet_id = serializers.IntegerField(required=True)
    tree_id = serializers.IntegerField(required=True)

    def create(self, validated_data):
        return Analysis.objects.create(**validated_data)

'''

    def update(self, instance, validated_data):
        """
        Update and return an existing `Snippet` instance, given the validated data.
        """
        instance.title = validated_data.get('title', instance.title)
        instance.code = validated_data.get('code', instance.code)
        instance.linenos = validated_data.get('linenos', instance.linenos)
        instance.language = validated_data.get('language', instance.language)
        instance.style = validated_data.get('style', instance.style)
        instance.save()
        return instance
'''
