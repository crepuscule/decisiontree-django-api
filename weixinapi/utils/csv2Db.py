import pymysql

DBHOST = '47.95.196.25'
DBUSER = 'root'
DBPWD  = '12345678'
DBNAME = 'db_dataset'

# I.1 从一个有表头的csv文件读取数据
def readFromCSV(filename='data'):
    f = open(filename)
    datas = []
    # 开始读取数据集
    for line in f:
        newline = line.strip('\n').split(',')
        # 插入到datas
        datas.append(newline)
    f.close()
    #print(datas)
    #labels = datas[0][:len(datas[1])-1] #这里根据第2行的数据列数来决定labels裁剪多少，labels列数总比dataset列数少1
    labels = datas[0]
    #如果labels少写了结果列，则比数据集列数少1,加上即可
    if len(labels) == len(datas[1])-1:
        labels.append('class')
    dataSet = datas[1:] #第二行开始就是数据集了
    return dataSet,labels


def writeToDB(pathname,filename):
    dataSet,labels = readFromCSV(pathname+filename)
    db=pymysql.connect(DBHOST,DBUSER,DBPWD,DBNAME,charset="utf8")
    cursor = db.cursor()
    #先判断是否存在同名的表格
    filename = filename.replace(".csv","")
    print('incstodb filename:'+filename)
    serial = 0 
    querySql = "show tables like '%s'" % (filename)
    while True:
        cursor.execute(querySql)
        effectRow = cursor.rowcount
        print('是否存在该表名:',effectRow)
        if effectRow >= 1:
            serial += 1
            querySql = "show tables like '%s'" % (filename+'_'+str(serial))
        else:
            #如果serial为0,说明没有重复的数据表名
            if serial != 0:
                filename = filename+'_'+str(serial)               
            break
    #再根据filename,labels创建表格结构

    createSql='create table `%s`(`id` int primary key auto_increment,' % (filename)
    for value in labels:
        createSql+='`%s` varchar(255) not null,' % (value)
    createSql = createSql[:-1]
    createSql+=')engine=innoDB default charset=utf8;'
    try:
        #print('',end='')
        #print(createSql)
        cursor.execute(createSql)
    except Exception as e:
        db.close()
        print(e)
        return -1
    
    insertSql = "insert into `%s`(" % (filename)
    for value in labels:
        insertSql += "`%s`," % (value)
    #insertSql += '`result`) values('
    insertSql = insertSql[:-1]
    insertSql += ') values('
    bakSql = insertSql
    #insertSql前半部分是共用的
    for line in dataSet:
        insertSql = bakSql
        #再将数据插入数据表
        for value in line:
            insertSql+="'%s'," % (value)
        insertSql = insertSql[:-1]
        insertSql += ");"
        try:
            #print('',end='')
            #print(insertSql)
            cursor.execute(insertSql)
            db.commit()
        except Exception as e:
            print(e)
            db.rollback()
            db.close()
            return -2
    db.close()
    #最后返回真实的数据表名称和记录的条数
    print(filename,len(dataSet),labels)
    return filename,len(dataSet),labels
    

#print(writeToDB('../uploads/','playtennis_one.csv'))
