import arcpy
import numpy as np
import datetime
import pandas as pd
import csv

arcpy.env.workspace = r"D:\Zatka\MostMHD_10_23.gdb"
arcpy.env.overwriteOutput = 1
arcpy.env.qualifiedFieldNames = 0

rychlost_m_s = 6.38     #tj. 23 km/h

def slovnik_zastavky_id(zaznamy_polohy):
    konecna_id = {} #formát id_zastavky:název zastávky

    with arcpy.da.SearchCursor(zaznamy_polohy, ["PASPORT", "NAZEV"]) as cursor:
        for row in cursor:
            atr1 = row[0]
            atr2 = row[1]
            
            if atr1 not in konecna_id:
                konecna_id[atr1] = atr2

    return(konecna_id)

def zaznam_polohy_to_point_geometry(zaznamy_polohy, linka, cilova_zastavka_id, cas, smer_1_2=None):
    """
    Extrahuje geometrii a atributy záznamu polohy, který je nejblíže CPU. Vybíráno je dle zadané linky, směru a času záznamu.
    
    Parametry:
    zaznamy_polohy (str): Cesta k datové sadě s polohovými záznamy.
    linka (int): Číslo linky, pro kterou se mají záznamy vyhledat.
    cilova_zastavka_id (int): ID cílové zastávky pro filtraci záznamů.
    cas (datetime.datetime): Časový okamžik, pro který se mají záznamy vyhledat.
    smer_1_2 (int, optional): Specifikuje směr jízdy, pokud je potřeba rozlišení.
    """
    cas_dotaz = cas
    if linka == 14 and cilova_zastavka_id == 201:
        cas_dotaz = cas_dotaz - datetime.timedelta(minutes=3)
        print(cas_dotaz)
    cas_plus1sec = cas_dotaz + datetime.timedelta(seconds=1)
    sql = f"CISLO_LINKY = {linka} AND CILOVA_ZASTAVKA_ID = {cilova_zastavka_id} AND (TIME_DATE = date '{cas_dotaz}' OR TIME_DATE = date '{cas_plus1sec}')"
    arcpy.management.MakeTableView(zaznamy_polohy, "vybrano", sql)
    arcpy.Sort_management("vybrano", "vybrano_s", [["vzdalenost_krizovatka", "DESCENDING"]])
    with arcpy.da.SearchCursor("vybrano_s ", ["SHAPE@", "CISLO_LINKY", "CILOVA_ZASTAVKA_ID", 'TIME_DATE']) as cursor:   #vybírá nejbližší bod aatributy z něj ukládá
        geometry = None
        a1 = None
        a2 = None
        a3 = None
        for row in cursor:
            geometry = row[0]
            a1 = row[1]
            a2 = row[2]
            a3 = row[3]
        if smer_1_2 == None:
            arcpy.Delete_management("vybrano_sorted")
            return([geometry, a1, a2, a3]) #vrací ["SHAPE@", "CISLO_LINKY", "CILOVA_ZASTAVKA_ID", "TIME_DATE"
        else:
            arcpy.Delete_management("vybrano_sorted")
            return([geometry, a1, a2, a3, smer_1_2]) #vrací ["SHAPE@", "CISLO_LINKY", "CILOVA_ZASTAVKA_ID", "TIME_DATE", smer_1_2    

def fc_do_geometrie(fc, klicovy_atribut):
    slovnik_geometrii = {}
    with arcpy.da.SearchCursor(fc, ["SHAPE@", f"{klicovy_atribut}"]) as cursor:
        for row in cursor: 
            geometry = row[0]
            atribut = row[1]
            slovnik_geometrii[atribut] = geometry
    return(slovnik_geometrii)
    
def dopocti_cas_prijezdu(zaznam_polohy_point, slovnik_sloupky_geom, linka, cilova_zastavka_id, cas_zaznamu, za_semaforem, smer_1_2=None):
    """
    Vrací odhadovaný čas příjezdu vozidla k odpovídajícímu odjezdovému sloupku.
    """
    if smer_1_2 == None:
        id_sloupku, pres_krizovatku, cekani_semafor_orig = slovnik_linky_info[(linka, cilova_zastavka_id)]
    else:
        id_sloupku, pres_krizovatku, cekani_semafor_orig = slovnik_linky_info[(linka, cilova_zastavka_id, smer_1_2)]

    id_sloupku_poloha = slovnik_sloupky_geom[id_sloupku]
    cas_prijezdu = cas_zaznamu + datetime.timedelta(seconds=(id_sloupku_poloha.distanceTo(zaznam_polohy_point)/rychlost_m_s))
    if linka == 14 and cilova_zastavka_id == 201:
        cas_prijezdu = cas_prijezdu - datetime.timedelta(minutes=2)
    return(cas_prijezdu)

def seznam_casu_hodiny(prvni, posledni, minuta):
    list_hodin = []
    for h in range(prvni, posledni+1):
        a = datetime.time(h,minuta)
        list_hodin.append(a)
    return(list_hodin)

def seznam_casu_hodiny_2(prvni, posledni, minuta):
    list_hodin = []
    for h in range(prvni, posledni+1,2):
        a = datetime.time(h,minuta)
        list_hodin.append(a)
    return(list_hodin)


slovnik_linky_info = {          #formát (cislo_linky, id_cilove_zastavky):[id_odjezdoveho_sloupku (PASP_SLO), pres_krizovatku (T/F ), střední doba čekání na semaforu]
    (4,26):["20/1", False, 0],
    (4,3):["20/2", False, 0],
    (13,207):["201/2", False, 0],
    (13,210):["201/2", False, 0],
    (13,205):["201/2", False, 0],
    (13,249):["201/2", False, 0],
    (13,225):["201/1", False, 0],
    (13,227):["201/1", False, 0],
    (14,244):["201/1", False, 0],
    (14,201):["201/1", False, 0]
}
 
slovnik_sloupky_index = { #zde indexuji sloupky, pomocí indexů budu hledat pozici přestupového času v tabulce stredni_cas_prestupu
    "20/1":0,
    "20/2":1,
    "201/1":2,
    "201/2":3
}

#výběr odpovídajících bodů
stred_krizovatky = arcpy.PointGeometry(arcpy.Point(-791993.10,-979099.20), 5514)
buffer = stred_krizovatky.buffer(3000)
arcpy.CopyFeatures_management(buffer, "buffer_3000")
arcpy.analysis.Clip("zaznamy_polohy_ocisteno", "buffer3000", "zaznamy_polohy_litvinov_3000")

arcpy.CopyFeatures_management(stred_krizovatky, "stred_krizovatky")
arcpy.analysis.Near("zaznamy_polohy_litvinov_3000", "stred_krizovatky", field_names = [["NEAR_DIST", "vzdalenost_krizovatka"]])

#tvorba slovníků geometrií indexovaných vždy druhým vkládaným argumentem
slovnik_sloupky_geom = fc_do_geometrie("zastavky_litvinov", "PASP_SLO")
slovnik_zona_zastavky = fc_do_geometrie("zony_zastavek_litvinov", "ID_SLOUPKU")
#slovnik_zona_za_semaforem = fc_do_geometrie("za_semaforem_zona_litvinov", "ID_SLOUPKU") #není v litvínově

slovnik_konecne = slovnik_zastavky_id("zastavky_orig") #využiji při zápisu názvu zastávky na základě ID do výstupu

#stredni_cas_prestupu_bez_cekani jednotka sekundy
cp_bez_cekani =np.array(

        [[0,0,15,25],
        [0,0,25,10],
        [15,25,0,35],
        [25,10,35,0]]

    )

#stredni_delka_cekani_na_semaforu - v Litvinove neni
cp_stredni_semafor= np.array(

        [[0,0,0,0],
        [0,0,0,0],
        [0,0,0,0],
        [0,0,0,0]]
    )

#následuje seznam odjezdových kombinací v dané časy, nejprve pro všední dny (cases_vsedni_dny), poté pro nepracovni (cases_vikendy)
cases_vsedni_dny = {
    "case16" : {"casy": [datetime.time(20, 0)],
               "linky": [(13,205), (14,244), (14,201), (13,225), (4,3), (4,26)]},
    "case17" : {"casy": [datetime.time(21, 0)],
               "linky": [(13,207), (14,244), (14,201), (13,225), (4,3), (4,26)]},
    "case18" : {"casy": [datetime.time(22, 0)],
               "linky": [(13,207), (14,201), (13,225), (4,3), (4,26)]},
    "case19" : {"casy": [datetime.time(19, 30)],
               "linky": [(13,210), (13,225), (4,3), (4,26)]},
    "case20" : {"casy": [datetime.time(20, 30)],
               "linky": [(13,249), (13,227), (4,3), (4,26)]},
    "case21" : {"casy": [datetime.time(21, 30)],
               "linky": [(13,205), (13,225), (4,3), (4,26)]},
    "case22" : {"casy": [datetime.time(22, 30)],
               "linky": [(13,210), (13,227), (4,3), (4,26)]}
}
cases_vikendy = {
    "case23" : {"casy": [datetime.time(5,0)],
               "linky": [(13,210), (13,227), (4,3)]},
    "case24" : {"casy": [datetime.time(6,0)],
               "linky": [(13,210), (13,225), (14,201), (4,3), (4,26)]},
    "case25" : {"casy": [datetime.time(7,0)],
               "linky": [(13,210), (13,227), (14,244), (4,3), (4,26)]},
    "case26" : {"casy": seznam_casu_hodiny(8,9,0)+seznam_casu_hodiny(18,20,0)+[datetime.time(11,0), datetime.time(13,0), datetime.time(15,0)], 
               "linky": [(13,210), (13,225), (14,244), (14,201), (4,3), (4,26)]},
    "case27" : {"casy": [datetime.time(21,0)],
               "linky": [(13,207), (13,225), (14,244), (14,201), (4,3), (4,26)]},
    "case28" : {"casy": [datetime.time(22,0)],
               "linky": [(13,207), (13,225), (4,3), (4,26)]},
    "case29" : {"casy": seznam_casu_hodiny(16,17,0)+[datetime.time(10,0), datetime.time(12,0), datetime.time(14,0)],
               "linky": [(13,210), (13,227), (14,244), (14,201), (4,3), (4,26)]},
    "case30" : {"casy": seznam_casu_hodiny_2(5,21,30),
               "linky": [(13,205), (13,225), (4,3), (4,26)]},
    "case31" : {"casy": seznam_casu_hodiny_2(6,18,30) + [datetime.time(22,30)],
               "linky": [(13,210), (13,225), (4,3), (4,26)]},
    "case32" : {"casy": [datetime.time(20,33)],
               "linky": [(13,210), (13,227), (4,3), (4,26)]}
}

prvni = datetime.date(2023, 10, 1)
posledni = datetime.date(2023, 10, 31)
vsedni_dny = []
vikendy = []
akt = prvni
while akt <= posledni:
    if akt == datetime.date(2023, 10, 28):  #svátek (v případě 2023 sice sobota, ale přesto uvedeno)
        vikendy.append(akt)
    elif akt.weekday() < 5:
        vsedni_dny.append(akt)
    else:
        vikendy.append(akt)
    akt = akt + datetime.timedelta(days=1)

tabulky_prestupu = {}

#běh algoritmu každou uspořádanou dvojici linek sjíždějících se v daný cas a den - rozdělené sykly pro vsedni dny a vikendy
#princip tvorbu tabulek case je popsán v textu bakalářské práce, nechybí ani schématu postupu
for datum in vsedni_dny:
    for case_key in cases_vsedni_dny.keys():
        case = cases_vsedni_dny[case_key]
        for cas in case["casy"]:
            cas_datum = datetime_obj = datetime.datetime.combine(datum, cas)
            pocet_linek = len(case["linky"])
            tabulka_prijezd_odjezd = np.empty((pocet_linek,pocet_linek), dtype=list)
            for i in range(pocet_linek):
                for j in range(pocet_linek):
                    tabulka_prijezd_odjezd[i, j] = [0, 0, 0]
            l = 0
            for linka in case["linky"]:
                if len(linka) == 3:     #pokud má linka přídavné rozlišení směru (to má, pokud je polookružní)
                    bod_zaznamu = zaznam_polohy_to_point_geometry("zaznamy_polohy_litvinov_3000", linka[0], linka[1], cas_datum, linka[2])
                else:
                    bod_zaznamu = zaznam_polohy_to_point_geometry("zaznamy_polohy_litvinov_3000", linka[0], linka[1], cas_datum)
                if bod_zaznamu[1] != None:
                    if len(bod_zaznamu) == 5:
                        sloupek_id = slovnik_linky_info[(bod_zaznamu[1], bod_zaznamu[2], bod_zaznamu[4])][0]
                        pres_krizovatku = slovnik_linky_info[(bod_zaznamu[1], bod_zaznamu[2], bod_zaznamu[4])][1]
                    else:
                        sloupek_id = slovnik_linky_info[(bod_zaznamu[1], bod_zaznamu[2])][0]
                        pres_krizovatku = slovnik_linky_info[(bod_zaznamu[1], bod_zaznamu[2])][1]
                    v_zastavce = None
                    v_zastavce = slovnik_zona_zastavky[sloupek_id].contains(bod_zaznamu[0])

                    if v_zastavce == True:
                        if linka in [(14, 201)]:
                            cas_prijezdu = cas_datum - datetime.timedelta(minutes=2)
                        cas_prijezdu = cas_datum
                    elif v_zastavce == False:
                        za_semaforem = None
                        if pres_krizovatku == True:
                            za_semaforem = slovnik_zona_za_semaforem[sloupek_id].contains(bod_zaznamu[0])
                        elif pres_krizovatku == False:
                            za_semaforem = True
                        if len(linka) == 3:
                            cas_prijezdu = dopocti_cas_prijezdu(bod_zaznamu[0], slovnik_sloupky_geom, linka[0], linka[1], cas_datum, za_semaforem, linka[2])
                        else:
                            cas_prijezdu = dopocti_cas_prijezdu(bod_zaznamu[0], slovnik_sloupky_geom, linka[0], linka[1], cas_datum, za_semaforem)
 
                else:
                    cas_prijezdu = datetime.datetime.combine(datum, datetime.time(23,59,59)) #doplnit nestihl ke vsem kombinacim - workaround nastavit casprijezdu na 23:59:59

                #   V TUTO CHVÍLI MÁM ČAS PŘÍJEZDU DANÉ LINKY NA ZASTÁVKU (cas_prijezdu)
                #   následuje přiřazení času odjezdu
                if linka == (4,3):
                    planovany_cas_odjezdu = cas_datum
                elif linka in [(4,26),(14,244)]:
                    planovany_cas_odjezdu = cas_datum + datetime.timedelta(minutes=2)
                else:
                    planovany_cas_odjezdu = cas_datum + datetime.timedelta(minutes=3)

                if linka == (14,244):
                    cas_odjezdu = cas_datum + datetime.timedelta(minutes=2)
                elif cas_prijezdu == datetime.datetime.combine(datum, datetime.time(23,59,59)):
                    cas_odjezdu = datetime.datetime.combine(datum, datetime.time(23,59,59))
                elif cas_prijezdu + datetime.timedelta(seconds=20) <= planovany_cas_odjezdu: #kalkuluji 20 sekund na nastup a vystup cestujicich
                    cas_odjezdu = planovany_cas_odjezdu
                elif cas_prijezdu + datetime.timedelta(seconds=20) > planovany_cas_odjezdu:
                    cas_odjezdu = cas_prijezdu + datetime.timedelta(seconds=20)
                for o in range(pocet_linek):
                    if l != o:
                        tabulka_prijezd_odjezd[l,o][0] = cas_prijezdu
                        tabulka_prijezd_odjezd[o,l][1] = cas_odjezdu
                        datum_cas_rozjezdu = cas_datum + datetime.timedelta(minutes=3)
                        tabulka_prijezd_odjezd[o,l][2] = datum_cas_rozjezdu
                    else:
                        tabulka_prijezd_odjezd[l,o][0] = None
                        tabulka_prijezd_odjezd[o,l][1] = None
                        tabulka_prijezd_odjezd[o,l][2] = None
                l+=1
            if case_key not in tabulky_prestupu:
                tabulky_prestupu[case_key] = []
            tabulky_prestupu[case_key].append(tabulka_prijezd_odjezd)

for datum in vikendy:
    for case_key in cases_vikendy.keys():
        case = cases_vikendy[case_key]
        for cas in case["casy"]:
            cas_datum = datetime_obj = datetime.datetime.combine(datum, cas)
            pocet_linek = len(case["linky"])
            tabulka_prijezd_odjezd = np.empty((pocet_linek,pocet_linek), dtype=list)
            for i in range(pocet_linek):
                for j in range(pocet_linek):
                    tabulka_prijezd_odjezd[i, j] = [0, 0, 0]
            l = 0
            for linka in case["linky"]:
                if len(linka) == 3:     #pokud má linka přídavné rozlišení směru (to má, pokud je polookružní)
                    bod_zaznamu = zaznam_polohy_to_point_geometry("zaznamy_polohy_litvinov_3000", linka[0], linka[1], cas_datum, linka[2])
                else:
                    bod_zaznamu = zaznam_polohy_to_point_geometry("zaznamy_polohy_litvinov_3000", linka[0], linka[1], cas_datum)
                if bod_zaznamu[1] != None:
                    if len(bod_zaznamu) == 5:
                        sloupek_id = slovnik_linky_info[(bod_zaznamu[1], bod_zaznamu[2], bod_zaznamu[4])][0]
                        pres_krizovatku = slovnik_linky_info[(bod_zaznamu[1], bod_zaznamu[2], bod_zaznamu[4])][1]
                    else:
                        sloupek_id = slovnik_linky_info[(bod_zaznamu[1], bod_zaznamu[2])][0]
                        pres_krizovatku = slovnik_linky_info[(bod_zaznamu[1], bod_zaznamu[2])][1]
                    v_zastavce = None
                    v_zastavce = slovnik_zona_zastavky[sloupek_id].contains(bod_zaznamu[0])
                    if v_zastavce == True:
                        if linka in [(14, 201)]:
                            cas_prijezdu = cas_datum - datetime.timedelta(minutes=3)
                        cas_prijezdu = cas_datum
                    elif v_zastavce == False:
                        za_semaforem = None
                        if pres_krizovatku == True:
                            za_semaforem = slovnik_zona_za_semaforem[sloupek_id].contains(bod_zaznamu[0])
                        elif pres_krizovatku == False:
                            za_semaforem = True
                        if len(linka) == 3:
                            cas_prijezdu = dopocti_cas_prijezdu(bod_zaznamu[0], slovnik_sloupky_geom, linka[0], linka[1], cas_datum, za_semaforem, linka[2])
                        else:
                            cas_prijezdu = dopocti_cas_prijezdu(bod_zaznamu[0], slovnik_sloupky_geom, linka[0], linka[1], cas_datum, za_semaforem)

                else:
                    cas_prijezdu = datetime.datetime.combine(datum, datetime.time(23,59,59)) #doplnit nestihl ke vsem kombinacim - workaround nastavit casprijezdu na 23:59:59

                #   V TUTO CHVÍLI MÁM ČAS PŘÍJEZDU DANÉ LINKY NA ZASTÁVKU (cas_prijezdu)
                #   následuje přiřazení času odjezdu
                if linka == (4,3):
                    planovany_cas_odjezdu = cas_datum
                elif linka in [(4,26),(14,244)]:
                    planovany_cas_odjezdu = cas_datum + datetime.timedelta(minutes=2)
                else:
                    planovany_cas_odjezdu = cas_datum + datetime.timedelta(minutes=3)

                if linka == (14,244):
                    cas_odjezdu = cas_datum + datetime.timedelta(minutes=2)
                elif cas_prijezdu == datetime.datetime.combine(datum, datetime.time(23,59,59)):
                    cas_odjezdu = datetime.datetime.combine(datum, datetime.time(23,59,59))
                elif cas_prijezdu + datetime.timedelta(seconds=20) <= planovany_cas_odjezdu: #kalkuluji 20 sekund na nastup a vystup cestujicich
                    cas_odjezdu = planovany_cas_odjezdu
                elif cas_prijezdu + datetime.timedelta(seconds=20) > planovany_cas_odjezdu:
                    cas_odjezdu = cas_prijezdu + datetime.timedelta(seconds=20)
                for o in range(pocet_linek):
                    if l != o:
                        tabulka_prijezd_odjezd[l,o][0] = cas_prijezdu
                        tabulka_prijezd_odjezd[o,l][1] = cas_odjezdu
                        datum_cas_rozjezdu = cas_datum + datetime.timedelta(minutes=3)
                        tabulka_prijezd_odjezd[o,l][2] = datum_cas_rozjezdu
                    else:
                        tabulka_prijezd_odjezd[l,o][0] = None
                        tabulka_prijezd_odjezd[o,l][1] = None
                        tabulka_prijezd_odjezd[o,l][2] = None
                l+=1
            if case_key not in tabulky_prestupu:
                tabulky_prestupu[case_key] = []
            tabulky_prestupu[case_key].append(tabulka_prijezd_odjezd)

databaze_prestupu = []
tabulky_prestupu_tf = tabulky_prestupu
for case_tf in tabulky_prestupu_tf:
    for tabulka in tabulky_prestupu_tf[case_tf]:
        for i in range(len(tabulka)):
            for j in range(len(tabulka)):
                if case_tf in cases_vsedni_dny:
                    linka_smer_prijezdova   =   cases_vsedni_dny[case_tf]["linky"][i]
                    linka_smer_odjezdova    =   cases_vsedni_dny[case_tf]["linky"][j]
                else:
                    linka_smer_prijezdova   =   cases_vikendy[case_tf]["linky"][i]
                    linka_smer_odjezdova    =   cases_vikendy[case_tf]["linky"][j]
                
                sloupek_prijezd_id      =   slovnik_sloupky_index[slovnik_linky_info[linka_smer_prijezdova][0]]
                sloupek_odjezd_id       =   slovnik_sloupky_index[slovnik_linky_info[linka_smer_odjezdova][0]]
                delka_presunu           =   int(cp_bez_cekani[sloupek_prijezd_id,sloupek_odjezd_id] + cp_stredni_semafor[sloupek_prijezd_id,sloupek_odjezd_id])
                cas_prijezdovy          =   tabulka[i, j][0]
                cas_odjezdovy           =   tabulka[i, j][1]
                datumcas_rozjezd        =   tabulka[i, j][2]
                if tabulka[i, j] == [None, None, None]:
                    stihlo_se = None
                elif cas_prijezdovy + datetime.timedelta(seconds=delka_presunu) <= cas_odjezdovy:
                    stihlo_se = True
                else:
                    stihlo_se = False

                if stihlo_se != None:
                    cpu                     =   "Litvínov"
                    o_kolik_cele            =   cas_odjezdovy - (cas_prijezdovy + datetime.timedelta(seconds=delka_presunu))
                    o_kolik_sekundy = o_kolik_cele.total_seconds()
                    if abs(o_kolik_sekundy)      >   3600:
                        o_kolik = None
                    else:
                        o_kolik = o_kolik_sekundy
                    cas_rozjezd             =   datumcas_rozjezd.time()
                    radek = [case_tf, linka_smer_prijezdova[0], slovnik_konecne[linka_smer_prijezdova[1]], linka_smer_prijezdova, linka_smer_odjezdova[0],slovnik_konecne[linka_smer_odjezdova[1]], linka_smer_odjezdova, cas_rozjezd, cas_prijezdovy, cas_odjezdovy, delka_presunu, stihlo_se, o_kolik, cpu]
                    if linka_smer_odjezdova != (14,201) and linka_smer_prijezdova[0] != linka_smer_odjezdova[0] and linka_smer_prijezdova != (14,244): 
                        databaze_prestupu.append(radek)
                      
print(databaze_prestupu)
print("Výpočet skončil, bude proveden zápis do výstupního souboru.")

#export do csv
soubor_csv = r"D:\Zatka\prestupy_databaze_litvinov.csv"
with open(soubor_csv, mode='a', newline='') as file:
    writer = csv.writer(file)
    for radek in databaze_prestupu:
        writer.writerow(radek) 