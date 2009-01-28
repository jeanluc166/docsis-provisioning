##$Id$
# -*- coding: utf8 -*-
import os
import pymssql, _mssql
import getpass
import MySQLdb
from ProvCon.dbui.database import CFG, Init
from ProvCon.dbui.di import rObject
Record = rObject
import atexit
import StringIO

def dictresult ( cr ):
    #assert isinstance( cr, pymssql.pymssqlCursor )
    result = []
    for r in cr.fetchall():
        rowresult = {}
        for desc, val in map(lambda x,y: (x,y), cr.description, r):
            rowresult[desc[0]] = val
        result.append(rowresult)
    return result

def close(db):
    print "EXIT"
    try:
        db.close()
    except:
        pass

def addObjectNote (obj, note, who=None):
    if isinstance (obj, orm.Record):
        objectid = obj.objectid
    else:
        objectid = obj
    note = orm.Record.EMPTY ( "note" )
    note.refobjectid = objectid
    note.who = who
    note.content = note
    note.write()

def setObjectFlag (obj, flagname):    
    if isinstance (obj, orm.Record):
        objectid = obj.objectid
    else:
        objectid = obj
    flag = orm.Record.EMPTY ( "object_flag" )
    flag.refobjectid = objectid
    flag.flagname = flagname
    flag.write()
    
    
if __name__=="__main__":
    DataErrors = StringIO.StringIO()
    
    #połączenie z bazą docsis-provisioning
    Init()    
        
    #polaczenie z SQLEXPRESS - bazą BOK
    #pw = getpass.getpass("Password for \\SQLEXPRESS\stansat:stansat@reklamy >")
    pw = "wajig05850_hax0r"
    stansatDB = pymssql.connect ( user = 'stansat', database = 'stansat', host = 'reklamy',
                                  password = pw )
    cr = stansatDB.cursor()
    
    #połączenie z bazą NetCon 2.0
    n2db = MySQLdb.connect ( db='techdb', user='netcon3', host='83.243.39.5', charset='utf8' )
    n2cr = n2db.cursor()
    
    #Pobieranie danych z NetCon 2.0
    n2cr.execute ( "SELECT * FROM customer" )
    n2_customer_all = dictresult (n2cr)
    n2_customer_idMap = {}
    n2_customer_nameMap = {}
    for c in n2_customer_all:        
        c['_imported'] = False
        c['_subscriberid'] = None
        c['IP'] = []
        c['MAC'] = []
        n2_customer_idMap[c['id']] = c
        n2_customer_nameMap[c['name']] = c
        
    n2cr.execute ( "SELECT *, int2ipstr(ip) as ipaddr FROM customer_ip_assignment" )
    n2_ip_all = dictresult(n2cr)    
    for i in n2_ip_all:
        n2_customer_idMap[i['customer']]['IP'].append (i)

    n2cr.execute ( "SELECT *, int2ipstr(dhcp_ip) as ipaddr FROM customer_known_mac" )
    n2_mac_all = dictresult(n2cr)    
    for i in n2_mac_all:
        n2_customer_idMap[i['customer']]['MAC'].append (i)
        
    atexit.register ( close, stansatDB )
    

    n_TOS = {}
    n_COS = {}
    n2o_intMap = {}
    n2o_tvMap = {}
    o_pakietIntIdx = {}
    p_pakietTVIdx = {}
        
    
    #Import pakietów dostępu do Internetu
    cr.execute ("SELECT * FROM PakietInternet")
    CFG.CX.query ( "DELETE FROM {0}.class_of_service".format(CFG.DB.SCHEMA) )
    CFG.CX.query ( "DELETE FROM {0}.type_of_service".format(CFG.DB.SCHEMA) )
    pakiet_all = dictresult (cr)
    pakiet_IdxMap = {}
    
    tosRec = Record.EMPTY ( "type_of_service" )
    tosRec.typeid = "INT"
    tosRec.name = "Internet"
    tosRec.official_name = "Dostęp do Internetu"
    tosRec.classmap = []
    tosRec.write()
    cosIdx = []
    for p in pakiet_all:
        pRec = Record.EMPTY ( "class_of_service" )
        pRec.classid = p["Index"]
        pRec.name = p["Nazwa"].decode("cp1250")
        pRec.official_name = pRec.name
        pRec.write()
        cosIdx.append ( pRec.objectid )
        pakiet_IdxMap[p["Index"]] = pRec
    tosRec.classmap = cosIdx
    tosRec.write()
    
    
    cr.execute ( "SELECT TOP 50 * FROM Klient" )
    klient_all = dictresult ( cr )
    cr.execute ( "SELECT * FROM DaneKlientInternet" )
    dki_all = dictresult ( cr )
    dki_IdxMap = {}
    for dki in dki_all:
        dki_IdxMap[dki["KlientIndex"]] = dki

    #cr.execute ( "SELECT * FROM DaneKlientTelewizja" )
    #dkt_all = dictresult ( cr )
    
    CFG.CX.query ( "DELETE FROM {0}.subscriber".format(CFG.DB.SCHEMA) )
    CFG.CX.query ( "DELETE FROM {0}.service".format(CFG.DB.SCHEMA) )
    CFG.CX.query ( "DELETE FROM {0}.ip_reservation".format(CFG.DB.SCHEMA) )
    CFG.CX.query ( "DELETE FROM {0}.mac_interface".format(CFG.DB.SCHEMA) )
    
    subscriber_oldIdxMap = {}
    
    for K in klient_all:        
        subRec = Record ( "subscriber" )
        subRec.subscriberid = K["Index"]        
        subRec.name = ( (K["Imie"] or "") + " " + (K["Nazwisko"] or "")).strip().decode ( "cp1250" ).encode('utf8')
        subRec.postaladdress = (K["AdresKorespondencji"] or "").decode("cp1250").strip()
        if len(subRec.postaladdress) == 0: subRec.postaladdress = None
        if K["EMail"]:
            subRec.email = [ K["EMail"].decode("cp1250").encode("utf8") ]
        subRec.telephone = []
        if K["TelefonStacjonarny"]: subRec.telephone.append ( K["TelefonStacjonarny"][:32].decode("cp1250").encode("utf8") )
        if K["TelefonKomorkowy"]: subRec.telephone.append ( K["TelefonKomorkowy"][:32].decode("cp1250").encode("utf8") )
        subRec.write()        
        if K["OdbiorFaktur"]: subRec.PARAM.ODBIOR_FAKTUR = K["OdbiorFaktur"]
        if K["Wyszukiwanie"]: subRec.PARAM.WYSZUKIWANIE = K["Wyszukiwanie"].decode ( "cp1250" )
        if K["wynajmuje"]: subRec.FLAGS.WYNAJMUJE = True
        if K["Koperta"]: subRec.FLAGS.KOPERTA = True
        if K["BrakZgodyNaPrzetwarzanieDanych"]: subRec.FLAGS.BRAK_ZGODY_PD = True
        skrot = K["Skrot"].decode("cp1250").encode('utf8')
        subRec.PARAM.SKROT = K["Skrot"].decode("cp1250")
        subscriber_oldIdxMap[K["Index"]] = subRec
            
        
            
    #Miejscowości    
    CFG.CX.query ( "DELETE FROM {0}.city".format(CFG.DB.SCHEMA) )
    cr.execute ( "SELECT [Index], Nazwa FROM Miejscowosc" )
    city_onMap = {}
    city_nameMap = {}
    for mIndex, mNazwa in cr.fetchall():        
        nRec = Record.EMPTY ( "city" )
        cityName = mNazwa.decode("cp1250")

        if cityName in city_nameMap:
            city_onMap[mIndex] = city_nameMap[cityName]        
            continue
            
        nRec.name = cityName
        nRec.handle = None
        try:
            nRec.write()
        except Record.DataManipulationError, e:
            print str(e)
        city_onMap[mIndex] = nRec
        city_nameMap[cityName] = nRec

    #Ulice
    cr.execute ( "SELECT [Index], Nazwa, Skrot FROM Ulica" )
    ulica_idMap = {}
    for uIndex, uNazwa, uSkrot in cr.fetchall():
        ulica_idMap[uIndex] = (uNazwa, uSkrot or "")
    
    cr.execute ( "SELECT [Index], Skrot, UlicaIndex, MiejscowoscIndex, NrDomu, NrMieszkania, KodPocztowy FROM Klient" )

    klient_localizationMap = {}
    city_street_objMap = {}
    building_objMap = {}
    location_objMap = {}
    klient_objMap = {}
    
    for kIndex, kSkrot, uIndex, mIndex, kNrDomu, kNrMieszkania, kKodPocztowy in cr.fetchall():
        if not (mIndex, uIndex) in city_street_objMap:
            uRec = Record.EMPTY ( "street" )
            try:
                name, handle = ulica_idMap[uIndex]
            except KeyError:
                print kIndex, kSkrot, "incomplete location data."
                continue
            uRec.name = name.decode("cp1250")
            uRec.handle = handle
            uRec.cityid = city_onMap[mIndex].objectid
            uRec.write()
            city_street_objMap[ (mIndex, uIndex) ] = uRec
        else:
            uRec = city_street_objMap[ (mIndex, uIndex) ] 
        
        if not uRec.objectid in building_objMap:
            building_objMap[uRec.objectid] = {}
        
        if not kNrDomu in building_objMap[uRec.objectid]:
            bRec = Record.EMPTY ( "building" )
            if kNrDomu is None:
                bRec.number = "<brak>"
            else:
                bRec.number = kNrDomu.decode ( "cp1250" )
            bRec.streetid = uRec.objectid
            bRec.postal_code = kKodPocztowy
            bRec.write()
            building_objMap[uRec.objectid][kNrDomu] = bRec
        else:
            bRec = building_objMap[uRec.objectid][kNrDomu]
            
        if not bRec.objectid in location_objMap:
            location_objMap[bRec.objectid] = {}
            
        if not kNrMieszkania  in location_objMap[bRec.objectid]:
            lRec = Record.EMPTY ( "location" )
            if kNrMieszkania == "NULL": kNrMieszkania = None
            lRec.number = kNrMieszkania
            lRec.buildingid = bRec.objectid
            lRec.write()
            location_objMap[bRec.objectid][kNrMieszkania] = lRec
        else:
            lRec = location_objMap[bRec.objectid][kNrMieszkania]

        klient_localizationMap[kIndex] = lRec

    for kIndex in subscriber_oldIdxMap:
        subRec = subscriber_oldIdxMap[kIndex]
        try:
            subRec.primarylocationid = klient_localizationMap[kIndex].objectid
            if klient_localizationMap[kIndex].number == "NULL":
                klient_localizationMap[kIndex].number = None
                klient_localizationMap[kIndex].write()                
        except KeyError:
            pass
        subRec.write()
    
    for K in klient_all:
        dki = dki_IdxMap[K["Index"]]

        subRec = subscriber_oldIdxMap[K["Index"]]
        
        srvRec = Record ( "service" )
        srvRec.subscriberid = subRec.objectid
        try:
            srvRec.classofservice = pakiet_IdxMap[dki["PakietIndex"]].objectid
        except KeyError:
            print "Service DKI key not found."
            continue
        srvRec.typeofservice = tosRec.objectid
        srvRec.locationid = klient_localizationMap[K["Index"]].objectid
        srvRec.write()
        
        n2c = None
        skrot = K["Skrot"].decode('cp1250').encode('utf8')
        
        if skrot in n2_customer_idMap:
            n2c = n2_customer_idMap[skrot]
        elif subRec.name in n2_customer_nameMap:
            n2c = n2_customer_nameMap[subRec.name]
        if n2c is None:
            DataErrors.write( "Data Error: Klient %s nie znaleziony w bazie Netcon 2.0\n" % (skrot))
            continue
        try:
            ip_id_map = {}
            for ip in n2c['IP']:
                iprRec = Record ( "ip_reservation" )
                iprRec.ownerid = srvRec.objectid
                iprRec.address = ip['ipaddr']                
                iprRec.write()
                ip_id_map[ip['ipaddr']] = iprRec.objectid
            
            for mac in n2c['MAC']:
                macRec = Record ( "mac_interface" )
                macRec.ownerid = srvRec.objectid
                macRec.mac = mac['mac']
                if mac['ipaddr'] is not None:
                    try:
                        macRec.ipreservationid = ip_id_map[mac['ipaddr']]
                    except KeyError:
                        DataErrors.write ( "MAC: %s (%s) ma przypisany nieznany adres IP.\n" % (mac['mac'], mac['customer']) )
                        pass
                macRec.write()
                
        except KeyError:
            pass
        
    print "#" * 80
    print "## DATA ERRORS ##"
    print DataErrors.getvalue()
            
            


    
    stansatDB.close()
    

    