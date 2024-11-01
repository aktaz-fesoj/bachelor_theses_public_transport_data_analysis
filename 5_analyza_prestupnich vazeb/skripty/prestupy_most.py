import arcpy
import numpy as np
import datetime
import csv

arcpy.env.workspace = r"D:\Zatka\MostMHD_10_23.gdb"
arcpy.env.overwriteOutput = 1
arcpy.env.qualifiedFieldNames = 0

rychlost_m_s = 6.38     #tj. 23 km/h

def slovnik_zastavky_id(zastavky):
    konecna_id = {} #formát id_zastavky:název zastávky

    with arcpy.da.SearchCursor(zastavky, ["PASPORT", "NAZEV"]) as cursor:
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
    cas_plus1sec = cas + datetime.timedelta(seconds=1)
    sql = f"CISLO_LINKY = {linka} AND CILOVA_ZASTAVKA_ID = {cilova_zastavka_id} AND (TIME_DATE = date '{cas}' OR TIME_DATE = date '{cas_plus1sec}')"
    arcpy.management.MakeTableView(zaznamy_polohy, "vybrano", sql)
    arcpy.Sort_management("vybrano", "vybrano_s", [["vzdalenost_krizovatka", "DESCENDING"]])
    with arcpy.da.SearchCursor("vybrano_s ", ["SHAPE@", "CISLO_LINKY", "CILOVA_ZASTAVKA_ID", 'TIME_DATE']) as cursor:
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

    stred_krizovatky = arcpy.PointGeometry(arcpy.Point(-791294.39,-989095.27), 5514)
    id_sloupku_poloha = slovnik_sloupky_geom[id_sloupku]

    if pres_krizovatku == True:
        if za_semaforem == True:
            cas_prijezdu = cas_zaznamu + datetime.timedelta(seconds=id_sloupku_poloha.distanceTo(zaznam_polohy_point)/rychlost_m_s)
        elif za_semaforem == False:
            cas1 = (id_sloupku_poloha.distanceTo(stred_krizovatky)/rychlost_m_s)
            cas2 = (stred_krizovatky.distanceTo(zaznam_polohy_point)/rychlost_m_s)
            cas3 = cekani_semafor_orig

            cas_prijezdu = cas_zaznamu + datetime.timedelta(seconds=(cas1+cas2+cas3))
    else:
        cas_prijezdu = cas_zaznamu + datetime.timedelta(seconds=(id_sloupku_poloha.distanceTo(zaznam_polohy_point)/rychlost_m_s))

    return(cas_prijezdu)

def seznam_casu_hodiny(prvni, posledni, minuta):
    list_hodin = []
    for h in range(prvni, posledni+1):
        a = datetime.time(h,minuta)
        list_hodin.append(a)
    return(list_hodin)


slovnik_linky_info = {          #formát (cislo_linky, id_cilove_zastavky):[id_odjezdoveho_sloupku (PASP_SLO), pres_krizovatku (T/F ), střední doba čekání na semaforu]
    (2,1):["6/2", False, 0],
    (2,111):["6/2", False, 0],
    (2,9):["6/1", False, 0],
    (4,3):["6/2", False, 0],
    (4,26):["6/1", False, 0],
    (5,185):["142/2", True, 30],
    (5,178):["142/2", True, 30],
    (5,179):["142/2", True, 30],
    (5,135):["142/3", True, 30],
    (16,322,1):["142/3", True, 30], #odjezd na Soud
    (16,135,1):["142/3", True, 30], #odjezd na Soud
    (16,322,2):["142/4", True, 30], #odjezd na 1. náměstí
    (16,135,2):["142/4", True, 30], #odjezd na 1. náměstí
    (17,111,1):["142/4", True, 30], #odjezd na 1. náměstí
    (17,111,2):["142/5", True, 30], #odjezd na Zahražany
    (20,109):["142/1", True, 30],
    (20,180):["142/1", True, 30],
    (20,135):["142/3", True, 30],
    (22,163):["142/1", True, 30],
    (22,135):["142/3", True, 30],
    (30,135,1):["142/2", True, 30], #odjezd na 1. náměstí
    (30,135,2):["142/1", True, 30], #odjezd na Nemocnici
}
 
slovnik_sloupky_index = { #zde indexuji sloupky, pomocí indexů budu hledat pozici přestupového času v tabulce stredni_cas_prestupu
    "6/1":0,
    "6/2":1,
    "142/1":2,
    "142/2":3,
    "142/3":4,
    "142/4":5,
    "142/5":6
}

#výběr odpovídajících bodů
stred_krizovatky = arcpy.PointGeometry(arcpy.Point(-791294.39,-989095.27), 5514)
arcpy.CreateFeatureclass_management(arcpy.env.workspace, "bod_krizovatky", geometry_type="POINT", spatial_reference=arcpy.SpatialReference(5514))
with arcpy.da.InsertCursor("bod_krizovatky", ["SHAPE@"]) as cursor:
    cursor.insertRow([stred_krizovatky])
buffer = stred_krizovatky.buffer(3000)
arcpy.Buffer_analysis("bod_krizovatky", "buffer3000", 3000)
arcpy.analysis.Clip("zaznamy_polohy_ocisteno", "buffer3000", "zaznamy_polohy_prior_3000")

arcpy.CopyFeatures_management(stred_krizovatky, "stred_krizovatky")
arcpy.analysis.Near("zaznamy_polohy_prior_3000", "stred_krizovatky", field_names = [["NEAR_DIST", "vzdalenost_krizovatka"]])

print("vytvořeno")
#tvorba slovníků geometrií indexovaných vždy druhým vkládaným argumentem
slovnik_sloupky_geom = fc_do_geometrie("zastavky_prior", "PASP_SLO")
slovnik_zona_zastavky = fc_do_geometrie("zony_zastavek", "ID_SLOUPKU")
slovnik_zona_za_semaforem = fc_do_geometrie("zona_za_semaforem", "ID_SLOUPKU")

slovnik_konecne = slovnik_zastavky_id("zastavky_orig")   #využiji při zápisu názvu zastávky na základě ID do výstupu

#stredni_cas_prestupu_bez_cekani jednotka sekundy
cp_bez_cekani =np.array(

        [[0,58,52,27,39,57,53],
        [58,0,38,59,46,89,26],
        [52,38,0,46,80,76,54],
        [27,59,46,0,52,30,75],
        [39,46,80,52,0,82,44],
        [57,89,76,30,82,0,105],
        [53,26,54,75,44,105,0]]

    )

#stredni_delka_cekani_na_semaforu
cp_stredni_semafor= np.array(

        [[0,35,57,25,22,25,56],
        [35,0,18,49,17,49,25],
        [53,18,0,31,42,31,25],
        [22,56,31,0,22,0,56],
        [26,35,35,26,0,26,17],
        [22,56,31,0,22,0,56],
        [43,18,18,43,17,43,0]]
    )

#následuje seznam odjezdových kombinací v dané časy, nejprve pro všední dny (cases_vsedni_dny), poté pro nepracovni (cases_vikendy)
cases_vsedni_dny = {
    "case1" : {"casy": seznam_casu_hodiny(20,22,7),
               "linky": [(2,1), (4,26), (17,111,2), (20,109), (22,135), (30,135,1)]},
    "case2" : {"casy": seznam_casu_hodiny(19,22,36),
               "linky": [(2,1), (4,26), (17,111,2), (20,135), (22,163), (30,135,1)]},
    "case3" : {"casy": [datetime.time(20, 21), datetime.time(22, 21)],
               "linky": [(2,9), (4,3), (5,178), (5,135), (17,111,1)]},
    "case4" : {"casy": [datetime.time(21, 21)],
               "linky": [(2,9), (4,3), (5,179), (5,135), (17,111,1)]},
    "case5" : {"casy": seznam_casu_hodiny(19,21,51),
               "linky": [(2,9), (4,3), (5,185), (5,135), (17,111,1)]},
    "case6" : {"casy": [datetime.time(22, 51)],
               "linky": [(4,3), (5,185), (5,135), (17,111,1)]},
}
cases_vikendy = {
    "case7" : {"casy": [datetime.time(5, 7)],
               "linky": [(2,1), (4,26), (20,109), (22,135), (30,135,1)]},
    "case8" : {"casy": seznam_casu_hodiny(6,9,7)+(seznam_casu_hodiny(19,22,7)),
               "linky": [(2,1), (4,26), (17,111,2), (20,109), (22,135), (30,135,1)]},
    "case9" : {"casy": seznam_casu_hodiny(10,18,7),
               "linky": [(2,1), (4,26), (17,111,2), (20,180), (22,135), (30,135,1)]},
    "case10" : {"casy": seznam_casu_hodiny(5,22,36), 
               "linky": [(2,1), (4,26), (17,111,2), (20,135), (22,163), (30,135,1)]},
    "case11" : {"casy": seznam_casu_hodiny(5,6,21)+seznam_casu_hodiny(21,22,21),
               "linky": [(2,9), (4,3), (5,178), (5,135), (17,111,1)]},
    "case12" : {"casy": seznam_casu_hodiny(7,8,21)+(seznam_casu_hodiny(17,20,21)),
               "linky": [(2,9), (4,3), (5,178), (5,135), (16,135,1), (17,111,1)]},
    "case13" : {"casy": seznam_casu_hodiny(9,16,21),
               "linky": [(2,9), (4,3), (5,178), (5,135), (16,322,1), (17,111,1)]},
    "case14" : {"casy": seznam_casu_hodiny(5,21,51),
               "linky": [(2,9), (4,3), (5,185), (5,135), (17,111,1)]},
    "case15" : {"casy": [datetime.time(22, 51)],
               "linky": [(4,3), (5,185), (5,135), (17,111,1)]}
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
                    bod_zaznamu = zaznam_polohy_to_point_geometry("zaznamy_polohy_prior_3000", linka[0], linka[1], cas_datum, linka[2])
                else:
                    bod_zaznamu = zaznam_polohy_to_point_geometry("zaznamy_polohy_prior_3000", linka[0], linka[1], cas_datum)
                if bod_zaznamu[1] != None:
                    if len(bod_zaznamu) == 5:
                        sloupek_id = slovnik_linky_info[(bod_zaznamu[1], bod_zaznamu[2], bod_zaznamu[4])][0]
                        pres_krizovatku = slovnik_linky_info[(bod_zaznamu[1], bod_zaznamu[2], bod_zaznamu[4])][1]
                    else:
                        sloupek_id = slovnik_linky_info[(bod_zaznamu[1], bod_zaznamu[2])][0]
                        pres_krizovatku = slovnik_linky_info[(bod_zaznamu[1], bod_zaznamu[2])][1]
                    v_zastavce = None
                    v_zastavce = slovnik_zona_zastavky[sloupek_id].contains(bod_zaznamu[0])

                    #následuje výpočet času příjezdu
                    if v_zastavce == True:
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
                    cas_prijezdu = datetime.datetime.combine(datum, datetime.time(23,59,59)) #bod záznamu nebyl nalezen - > chci doplnit nestihl ke vsem kombinacim -> workaround = nastavit casprijezdu na 23:59:59

                #   V TUTO CHVÍLI MÁM ČAS PŘÍJEZDU DANÉ LINKY NA ZASTÁVKU (cas_prijezdu)
                #   následuje přiřazení času odjezdu
                if linka == (30,135,2):
                    planovany_cas_odjezdu = cas_datum + datetime.timedelta(minutes=6)
                else:
                    if cas_datum.minute == 7:
                        planovany_cas_odjezdu = cas_datum + datetime.timedelta(minutes=3)
                    elif cas_datum.minute in [36, 21, 51]:
                        planovany_cas_odjezdu = cas_datum + datetime.timedelta(minutes=4)

                if cas_prijezdu == datetime.datetime.combine(datum, datetime.time(23,59,59)):
                    cas_odjezdu = datetime.datetime.combine(datum, datetime.time(23,59,59))
                elif cas_prijezdu + datetime.timedelta(seconds=20) <= planovany_cas_odjezdu: # kalkuluji 20 sekund na nastup a vystup cestujicich
                    cas_odjezdu = planovany_cas_odjezdu
                elif cas_prijezdu + datetime.timedelta(seconds=20) > planovany_cas_odjezdu:
                    cas_odjezdu = cas_prijezdu + datetime.timedelta(seconds=20)
                for o in range(pocet_linek):
                    if l != o:
                        tabulka_prijezd_odjezd[l,o][0] = cas_prijezdu
                        tabulka_prijezd_odjezd[o,l][1] = cas_odjezdu
                        if cas_datum.minute == 7:
                            datum_cas_rozjezdu = cas_datum + datetime.timedelta(minutes=3)
                        else:
                            datum_cas_rozjezdu = cas_datum + datetime.timedelta(minutes=4)
                        tabulka_prijezd_odjezd[o,l][2] = datum_cas_rozjezdu
                    else:
                        tabulka_prijezd_odjezd[l,o][0] = None
                        tabulka_prijezd_odjezd[o,l][1] = None
                        tabulka_prijezd_odjezd[o,l][2] = None
                l+=1
            if case_key not in tabulky_prestupu:
                tabulky_prestupu[case_key] = []
            tabulky_prestupu[case_key].append(tabulka_prijezd_odjezd)
            print("prvni_beh")

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
                if len(linka) == 3: #pokud má linka přídavné rozlišení směru (to má, pokud je polookružní)
                    bod_zaznamu = zaznam_polohy_to_point_geometry("zaznamy_polohy_prior_3000", linka[0], linka[1], cas_datum, linka[2])
                else:
                    bod_zaznamu = zaznam_polohy_to_point_geometry("zaznamy_polohy_prior_3000", linka[0], linka[1], cas_datum)
                if bod_zaznamu[1] != None:
                    if len(bod_zaznamu) == 5:
                        sloupek_id = slovnik_linky_info[(bod_zaznamu[1], bod_zaznamu[2], bod_zaznamu[4])][0]
                        pres_krizovatku = slovnik_linky_info[(bod_zaznamu[1], bod_zaznamu[2], bod_zaznamu[4])][1]
                    else:
                        sloupek_id = slovnik_linky_info[(bod_zaznamu[1], bod_zaznamu[2])][0]
                        pres_krizovatku = slovnik_linky_info[(bod_zaznamu[1], bod_zaznamu[2])][1]
                    v_zastavce = None
                    v_zastavce = slovnik_zona_zastavky[sloupek_id].contains(bod_zaznamu[0])

                    #následuje výpočet času příjezdu
                    if v_zastavce == True:
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
                if linka == (30,135,2):
                    planovany_cas_odjezdu = cas_datum + datetime.timedelta(minutes=6)
                else:
                    if cas_datum.minute == 7:
                        planovany_cas_odjezdu = cas_datum + datetime.timedelta(minutes=3)
                    elif cas_datum.minute in [36, 21, 51]:
                        planovany_cas_odjezdu = cas_datum + datetime.timedelta(minutes=4)

                if cas_prijezdu == datetime.datetime.combine(datum, datetime.time(23,59,59)):
                    cas_odjezdu = datetime.datetime.combine(datum, datetime.time(23,59,59))
                elif cas_prijezdu + datetime.timedelta(seconds=30) <= planovany_cas_odjezdu: #kalkuluji 30 sekund na nastup a vystup cestujicich
                    cas_odjezdu = planovany_cas_odjezdu
                elif cas_prijezdu + datetime.timedelta(seconds=30) > planovany_cas_odjezdu:
                    cas_odjezdu = cas_prijezdu + datetime.timedelta(seconds=30)
                for o in range(pocet_linek):
                    if l != o:
                        tabulka_prijezd_odjezd[l,o][0] = cas_prijezdu
                        tabulka_prijezd_odjezd[o,l][1] = cas_odjezdu
                        if cas_datum.minute == 7:
                            datum_cas_rozjezdu = cas_datum + datetime.timedelta(minutes=3)
                        else:
                            datum_cas_rozjezdu = cas_datum + datetime.timedelta(minutes=4)
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
                    cpu                     =   "PRIOR"
                    o_kolik_cele            =   cas_odjezdovy - (cas_prijezdovy + datetime.timedelta(seconds=delka_presunu))
                    o_kolik_sekundy = o_kolik_cele.total_seconds()
                    if abs(o_kolik_sekundy)      >   3600:
                        o_kolik = None
                    else:
                        o_kolik = o_kolik_sekundy
                    cas_rozjezd             =   datumcas_rozjezd.time()
                    radek = [case_tf, linka_smer_prijezdova[0], slovnik_konecne[linka_smer_prijezdova[1]], linka_smer_prijezdova, linka_smer_odjezdova[0],slovnik_konecne[linka_smer_odjezdova[1]], linka_smer_odjezdova, cas_rozjezd, cas_prijezdovy, cas_odjezdovy, delka_presunu, stihlo_se, o_kolik, cpu]
                    databaze_prestupu.append(radek)
                      
print(databaze_prestupu)
print("Výpočet skončil, bude proveden zápis do výstupního souboru.")

#export do csv
soubor_csv = r"D:\Zatka\prestupy_databaze_most.csv"
with open(soubor_csv, mode='a', newline='') as file:
    writer = csv.writer(file)
    for radek in databaze_prestupu:
        writer.writerow(radek)