import arcpy

arcpy.env.workspace = r"D:\Zatka\MostMHD_10_23.gdb" #cesta k geodatabázi
arcpy.env.overwriteOutput = 1
arcpy.env.qualifiedFieldNames = 0

# ČÍSLA LINEK
#_______________

arcpy.MakeFeatureLayer_management("zaznamy_polohy_orig", "f_l")
linky_set = set()
with arcpy.da.SearchCursor("f_l", "CISLO_LINKY") as cursor:
    for row in cursor:
        linky_set.add(row[0])

print("Seznam linek objevujících se v naměřených bodových datech:")
print(linky_set)
arcpy.Delete_management("f_l")

arcpy.MakeFeatureLayer_management("linky", "f_l")
linky_set_linie = set()
with arcpy.da.SearchCursor("f_l", "LINKA") as cursor:
    for row in cursor:
        linky_set_linie.add(row[0])

print("Seznam linek objevujících se v seznamu linek:")
print(linky_set_linie)
print(len(linky_set))
arcpy.Delete_management("f_l")

diff_linky = linky_set - linky_set_linie

print("Rozdíl:")
print(diff_linky)

# POSLEDNÍ ZASTÁVKY
#_____________________

arcpy.MakeFeatureLayer_management("zaznamy_polohy_orig", "f_l")

cisla_vozidla_set = set()
with arcpy.da.SearchCursor("f_l", ["CISLO_LINKY", "CISLO_VOZIDLA"]) as cursor:
    for row in cursor:
        cisla_vozidla_set.add(row)

print("Seznam zaznamenaných cisel vozidel:")
sorted_set_descending = sorted(cisla_vozidla_set, reverse=False)

print(sorted_set_descending)
print(len(cisla_vozidla_set))

zastavky_zaznamy_set = set()
with arcpy.da.SearchCursor("f_l", "POSLEDNI_ZASTAVKA_NAME") as cursor:
    for row in cursor:
        zastavky_zaznamy_set.add(row[0])

print("Seznam zaznamenaných zastávek:")
print(zastavky_zaznamy_set)
print(len(zastavky_zaznamy_set))

arcpy.MakeFeatureLayer_management("zastavky_orig", "f_l_zast")
zastavky_set = set()
with arcpy.da.SearchCursor("f_l_zast", "NAZEV") as cursor:
    for row in cursor:
        zastavky_set.add(row[0])

print("Seznam zastávek:")
print(zastavky_set)
print(len(zastavky_set))

diff_zastavky = zastavky_zaznamy_set - zastavky_set
diff_zastavky_opak = zastavky_set - zastavky_zaznamy_set

print("Rozdíly:")
print(diff_zastavky)
print(diff_zastavky_opak)

#AZIMUTY
#__________

azimut_set = set()
with arcpy.da.SearchCursor("f_l", "AZIMUT") as cursor:
    for row in cursor:
        azimut_set.add(row[0])

sorted_set_descending = sorted(azimut_set, reverse=False)

print(sorted_set_descending)

#CILOVE ZASTÁVKY
#___________________

cilova_zast_set = set()
with arcpy.da.SearchCursor("f_l", "CILOVA_ZASTAVKA_NAME") as cursor:
    for row in cursor:
        cilova_zast_set.add(row[0])

print(cilova_zast_set)

cilova_zast_set = set()
with arcpy.da.SearchCursor("f_l", "CILOVA_ZASTAVKA_NAME") as cursor:
    for row in cursor:
        cilova_zast_set.add(row[0])

print(cilova_zast_set)
print(len(cilova_zast_set))

diff_cilove_zastavky = cilova_zast_set - zastavky_set
print(diff_cilove_zastavky)

arcpy.Delete_management("f_l")