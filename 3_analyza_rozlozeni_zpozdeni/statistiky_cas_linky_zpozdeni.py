import arcpy
import statistics
import pandas as pd

arcpy.env.workspace = r"D:\Zatka\MostMHD_10_23.gdb"
arcpy.env.overwriteOutput = 1
arcpy.env.qualifiedFieldNames = 0

def prumer_sloupce(input_layer, nazev_sloupce):
    list_zpozdeni = []
    with arcpy.da.SearchCursor(input_layer, [nazev_sloupce]) as search_cursor:
                for row in search_cursor:
                    zpozdeni = row[0]
                    list_zpozdeni.append(zpozdeni)
    if len(list_zpozdeni) > 0:
        return(statistics.mean(list_zpozdeni))
    else:
        return(0)

def filtrace_linky(body_shp, cislo_linky, vystup):
    arcpy.MakeFeatureLayer_management(body_shp, "fl_body")

    sql_podminka = f"CISLO_LINKY = {cislo_linky}"
    arcpy.SelectLayerByAttribute_management("fl_body", "NEW_SELECTION", sql_podminka)
    arcpy.CopyFeatures_management("fl_body", vystup)
    return(vystup)

def filtrace_bodu_dle_hodiny(body_shp, start, konec, linka, vystup):
    arcpy.MakeFeatureLayer_management(body_shp, "fl_body")

    sql_podminka = f"EXTRACT(HOUR FROM TIME_DATE) >= {start} AND EXTRACT(HOUR FROM TIME_DATE) <= {konec} AND CISLO_LINKY = {linka}"
    arcpy.SelectLayerByAttribute_management("fl_body", "NEW_SELECTION", sql_podminka)
    arcpy.CopyFeatures_management("fl_body", vystup)
    return(vystup)

arcpy.MakeFeatureLayer_management("zaznamy_polohy", "f_l")
linky_set = set()
with arcpy.da.SearchCursor("f_l", "CISLO_LINKY") as cursor:
    for row in cursor:
        linky_set.add(row[0])

print("Seznam linek objevujících se v naměřených bodových datech:")
print(linky_set)
dict_linky = {}
for cislo_linky in linky_set:    
    data_l = filtrace_linky("zaznamy_polohy", cislo_linky, r"body_linky")
    prumer_l = prumer_sloupce(data_l, "ZPOZDENI_MIN")
    dict_linky.update({cislo_linky:prumer_l})
print("Celkový:")
print(dict_linky)

dict_linky_6_12 = {}
for cislo_linky in linky_set:    
    data_li = filtrace_bodu_dle_hodiny("zaznamy_polohy", 6, 11, cislo_linky, r"body_linky")
    prumer_li = prumer_sloupce(data_l, "ZPOZDENI_MIN")
    dict_linky_6_12.update({cislo_linky:prumer_li})
print("6-12")
print(dict_linky_6_12)

dict_linky_12_17 = {}
for cislo_linky in linky_set:    
    data_lii = filtrace_bodu_dle_hodiny("zaznamy_polohy", 12, 16, cislo_linky, r"body_linky")
    prumer_lii = prumer_sloupce(data_l, "ZPOZDENI_MIN")
    dict_linky_12_17.update({cislo_linky:prumer_lii})
print("12-17")
print(dict_linky_12_17)

dict_linky_17_21 = {}
for cislo_linky in linky_set:    
    data_liii = filtrace_bodu_dle_hodiny("zaznamy_polohy", 17, 21, cislo_linky, r"body_linky")
    prumer_liii = prumer_sloupce(data_l, "ZPOZDENI_MIN")
    dict_linky_17_21.update({cislo_linky:prumer_liii})
print("17-21")
print(dict_linky_17_21)

data = {
    'celk': dict_linky,
    'rano': dict_linky_6_12,
    'odpo': dict_linky_12_17,
    'vecer': dict_linky_17_21
}

df = pd.DataFrame.from_dict(data, orient='index')

# uložení do excelu
excel_file = r"D:\Zatka\data_testovani_odevzdani_ zpozdeni_linek.xlsx"
df.to_excel(excel_file)

print("Data saved to", excel_file)




    