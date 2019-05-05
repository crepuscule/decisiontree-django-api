from django.urls import path,re_path

from . import views
app_name='[weixinapi]'

urlpatterns = [
    path('index/<int:tree_id>', views.index, name='index'),
    path('treegraph', views.treeGraph, name='treeGraph'),
    path('uploadtrain',views.uploadtrain),
    path('uploadtest',views.uploadtest),

    #path('dataset/<slug:dataset_id>', views.dataSet, name='dataset'),
    re_path(r'^dataset/(?P<dataset_id>[0-9a-z]*)', views.dataSet, name='dataset'),

    #path('tree/<int:tree_id>', views.tree, name='tree'),
    re_path(r'^tree/(?P<tree_id>[0-9a-z]*)', views.tree, name='tree'),

    #path('analysis/<int:analysis_id>', views.analysis, name='analysis'),
    re_path(r'^analysis/(?P<analysis_id>[0-9a-z]*)', views.analysis, name='analysis'),
    

]
