#!/usr/bin/env python

from wmf import wmf 
#import func_SIATA as fs
import pylab as pl
import numpy as np
from radar import radar 
import datetime as dt
import argparse
import textwrap
import os 
import pandas as pd

#Parametros de entrada del trazador
parser=argparse.ArgumentParser(
	prog='Genera Campos',
	formatter_class=argparse.RawDescriptionHelpFormatter,
	description=textwrap.dedent('''\
	Genera Campos para una cuenca cualquiera, se debe indicar la 
	fecha inicio, fecha fin, y el binario de la cuenca, este script 
	toma los datos que se encuentran en /mnt/RADAR/reprojected_data/
        '''))
#Parametros obligatorios
parser.add_argument("fechaI",help="(YYYY-MM-DD) Fecha de inicio de imagenes")
parser.add_argument("fechaF",help="(YYYY-MM-DD) Fecha de fin de imagenes")
parser.add_argument("cuenca",help="(Obligatorio) Ruta de la cuenca en formato .nc")
parser.add_argument("binCampos",help="(Obligatorio) Ruta donde se guarda el binario de lluvia")
parser.add_argument("-t","--dt",help="(Opcional) Delta de t en segundos",default = 300,type=float)
parser.add_argument("-u","--umbral",help="(Opcional) Umbral de lluvia minima",default = 0.0,type=float)
parser.add_argument("-v","--verbose",help="Informa sobre la fecha que esta agregando", 
	action = 'store_true')
parser.add_argument("-s","--super_verbose",help="Imprime para cada posicion las imagenes que encontro",
	action = 'store_true')
parser.add_argument("-o","--old",help="Si el archivo a generar es viejo, y se busca es actualizarlo y no borrarlo",
	default = 'no')
parser.add_argument("-1","--hora_1",help="Hora inicial de lectura de los archivos",default= None )
parser.add_argument("-2","--hora_2",help="Hora final de lectura de los archivos",default= None )

#lee todos los argumentos
args=parser.parse_args()

#-------------------------------------------------------------------------------------------------------------------------------------
#OBTIENE FECHAS Y DEJA ESE TEMA LISTO 
#-------------------------------------------------------------------------------------------------------------------------------------
#Obtiene las fechas por dias
datesDias = pd.date_range(args.fechaI,args.fechaF,freq='D')
a = pd.Series(np.zeros(len(datesDias)),index=datesDias)
a = a.resample('A',how = 'sum')
Anos = [i.strftime('%Y') for i in a.index.to_pydatetime()]

datesDias = [d.strftime('%Y%m%d') for d in datesDias.to_pydatetime()]

ListDays = []
ListRutas = []
for d in datesDias:
	try:
		L = os.listdir('/mnt/RADAR/reprojected_data/'+d)
		L = [l for l in L if any(map(l.startswith,Anos)) and l.endswith('010_120.bin')]
		ListDays.extend(L)
		Ruta = ['/mnt/RADAR/reprojected_data/'+d+'/'+l for l in L 
			if any(map(l.startswith,Anos)) and l.endswith('010_120.bin')]
		ListRutas.extend(Ruta)
	except:
		pass
ListDays.sort()
ListRutas.sort()
datesDias = [dt.datetime.strptime(d[:12],'%Y%m%d%H%M') for d in ListDays]
datesDias = pd.to_datetime(datesDias)

#Obtiene las fechas por Dt
textdt = '%d' % args.dt
#Agrega hora a la fecha inicial
if args.hora_1 <> None:
	inicio = args.fechaI+' '+args.hora_1
else:
	inicio = args.fechaI
#agrega hora a la fecha final
if args.hora_2 <> None:
	final = args.fechaF+' '+args.hora_2
else:
	final = args.fechaF

datesDt = pd.date_range(inicio,final,freq = textdt+'s')

PosDates = []
pos1 = 0
for d1,d2 in zip(datesDt[:-1],datesDt[1:]):
	pos2 = np.where((datesDias<d2) & (datesDias>=d1))[0].tolist()
	if len(pos2) == 0:
		pos2 = pos1
	else:
		pos1 = pos2
	PosDates.append(pos2)

#-------------------------------------------------------------------------------------------------------------------------------------
#CARGADO DE LA CUENCA SOBRE LA CUAL SE REALIZA EL TRABAJO DE OBTENER CAMPOS
#-------------------------------------------------------------------------------------------------------------------------------------
#Carga la cuenca del AMVA
cuAMVA = wmf.SimuBasin(0,0,0,0,rute = args.cuenca)
rad = radar.radar_process()

#-------------------------------------------------------------------------------------------------------------------------------------
#GENERA EL BINARIO DE CAMPOS PARA LA CUENCA 
#-------------------------------------------------------------------------------------------------------------------------------------

#si el binario el viejo, establece las variables para actualizar
if args.old == 'si':
	cuAMVA.rain_radar2basin_from_array(status='old',ruta_out=args.binCampos)

#Itera sobre las fechas para actualizar el binario de campos
datesDt = datesDt.to_pydatetime()
for dates,pos in zip(datesDt[1:],PosDates):
	rvec = np.zeros(cuAMVA.ncells)
	try:
		for p in pos:
			if args.super_verbose:
				print ListRutas[p]
			#Lee la imagen de radar para esa fecha
			rad.read_bin(ListRutas[p])
			rad.detect_clouds(umbral=500)
	                rad.ref = rad.ref * rad.binario
        	        rad.DBZ2Rain()
                	rvec += cuAMVA.Transform_Map2Basin(rad.ppt/12.0,radar.RadProp)
	except:
		rvec = np.zeros(cuAMVA.ncells)
	#Escribe el binario
	dentro = cuAMVA.rain_radar2basin_from_array(vec = rvec,
		ruta_out = args.binCampos,
		fecha = dates-dt.timedelta(hours = 5),
		dt = args.dt,
		umbral = args.umbral)
	if args.verbose:
		print dates,rvec.mean(), dentro
		print '-----------------------------------------'
cuAMVA.rain_radar2basin_from_array(status = 'close',
        ruta_out = args.binCampos)

