#! /usr/bin/python3
# Travelshed Mapping
# OpenTripPlanner Guide: http://docs.opentripplanner.org/en/latest/
# OpenTripPlanner API Doc: http://dev.opentripplanner.org/apidoc/1.0.0/index.html

import datetime
import requests
import geopandas as gpd
import pandas as pd
import numpy as np
import multiprocessing as mp

start=datetime.datetime.now()

pd.set_option('display.max_columns', None)
path='/home/mayijun/TRAVELSHED/'
#path='E:/'
#path='C:/Users/Yijun Ma/Desktop/D/DOCUMENT/DCP2018/TRAVELSHEDREVAMP/'
nyc=['36005','36047','36061','36081','36085']


# Load quadstate blokc point shapefile
bkpt=gpd.read_file(path+'shp/quadstatebkpt.shp')
bkpt.crs={'init': 'epsg:4326'}

# Set typical day
typicaldate='2018/06/06'

# Create arrival time list
arrivaltimeinterval=10 # in minutes
arrivaltimestart='07:00:00'
arrivaltimeend='10:00:00'
arrivaltimestart=datetime.datetime.strptime(arrivaltimestart,'%H:%M:%S')
arrivaltimeend=datetime.datetime.strptime(arrivaltimeend,'%H:%M:%S')
arrivaltimeincrement=arrivaltimestart
arrivaltime=[]
while arrivaltimeincrement<=arrivaltimeend:
    arrivaltime.append(datetime.datetime.strftime(arrivaltimeincrement,'%H:%M:%S'))
    arrivaltimeincrement+=datetime.timedelta(seconds=arrivaltimeinterval*60)

# Set maximum number of transfers
maxTransfers=3 # 4 boardings

# Set maximum walking distance
maxWalkDistance=805 # in meters

# Set cut off points between 0-120 mins
cutoffinterval=2 # in minutes
cutoffstart=0
cutoffend=120
cutoffincrement=cutoffstart
cutoff=''
while cutoffincrement<cutoffend:
    cutoff+='&cutoffSec='+str((cutoffincrement+cutoffinterval)*60)
    cutoffincrement+=cutoffinterval

# Definie travelshed function to generate isochrones and spatial join to Census Blocks
def travelshed(arrt):
    bk=bkpt.copy()
    url='http://localhost:8801/otp/routers/default/isochrone?batch=true&mode=WALK,BUS'
    url+='&fromPlace='+destination.loc[i,'latlong']+'&toPlace='+destination.loc[i,'latlong']
    url+='&arriveBy=true&date='+typicaldate+'&time='+arrt+'&maxTransfers='+str(maxTransfers)
    url+='&maxWalkDistance='+str(maxWalkDistance)+cutoff
    headers={'Accept':'application/json'}  
    req=requests.get(url=url,headers=headers)
    js=req.json()
    iso=gpd.GeoDataFrame.from_features(js,crs={'init': 'epsg:4326'})
    bk['T'+arrt[0:2]+arrt[3:5]]=999
    cut=range(cutoffend,cutoffstart,-cutoffinterval)
    bkiso=gpd.sjoin(bk,iso.loc[iso['time']==cut[0]*60],how='left',op='within')
    bkiso=bkiso.loc[pd.notnull(bkiso['time']),'blockid']
    bk.loc[bk['blockid'].isin(bkiso),'T'+arrt[0:2]+arrt[3:5]]=cut[0]-cutoffinterval/2
    for k in range(0,(len(cut)-1)):
        if (iso.loc[iso['time']==cut[k+1]*60,'geometry'].notna()).bool():
            if len(bk.loc[bk['T'+arrt[0:2]+arrt[3:5]]==cut[k]-cutoffinterval/2])!=0:
                try:
                    bkiso=gpd.sjoin(bk.loc[bk['T'+arrt[0:2]+arrt[3:5]]==cut[k]-cutoffinterval/2],
                                    iso.loc[iso['time']==cut[k+1]*60],how='left',op='within')
                    bkiso=bkiso.loc[pd.notnull(bkiso['time']),'blockid']
                    bk.loc[bk['blockid'].isin(bkiso),'T'+arrt[0:2]+arrt[3:5]]=cut[k+1]-cutoffinterval/2
                except ValueError:
                    print(destination.loc[i,'id']+' '+arrt+' '+
                          str(cut[k+1])+'-minute isochrone has no Census Block in it!')
            else:
                print(destination.loc[i,'id']+' '+arrt+' '+
                      str(cut[k])+'-minute isochrone has no Census Block in it!')
        else:
            print(destination.loc[i,'id']+' '+arrt+' '+
                  str(cut[k+1])+'-minute isochrone has no geometry!')
    bk['T'+arrt[0:2]+arrt[3:5]]=bk['T'+arrt[0:2]+arrt[3:5]].replace(999,np.nan)
    bk=bk.drop(['lat','long','geometry'],axis=1)
    bk=bk.set_index('blockid')
    return bk

# Define parallel multiprocessing function
def parallelize(data, func):
    pool = mp.Pool(len(data))
    dt = pd.concat(pool.map(func, data),axis=1)
    pool.close()
    pool.join()
    return dt

# Multiprocessing travelshed function for Port Authority (Bus)
if __name__=='__main__':
    destination=pd.DataFrame(columns=['id','latlong'])
    destination.loc[0,'id']='BUSPA'
    destination.loc[0,'latlong']='40.756561,-73.990277'
    for i in destination.index:
        df=parallelize(arrivaltime,travelshed)
        df['TTMEDIAN']=df.median(skipna=True,axis=1)
        df=df['TTMEDIAN'].sort_index()
        df.name=destination.loc[i,'id']
        df.to_csv(path+'angela/'+destination.loc[i,'id']+'.csv',index=True,header=True,na_rep=999)
    print(datetime.datetime.now()-start)

