import arcpy
import time
start_time = time.time()

arcpy.env.workspace = r"D:\Zatka\data"
arcpy.env.overwriteOutput = 1
arcpy.env.qualifiedFieldNames = 0

def delete_content(file_path):
    with open(file_path, 'w') as file:
        file.write('')

#Pročištění výstupních textových souborů
delete_content(r"D:\Zatka\output_linka_mimo.txt")
delete_content(r"D:\Zatka\output_koridor_mimo.txt")

arcpy.MakeFeatureLayer_management("linky_cele.shp", "f_l")
linky_set = set()
with arcpy.da.SearchCursor("f_l", "LINKA") as cursor:
    for row in cursor:
        linky_set.add(row[0])

linky_list = list(linky_set)

print(linky_list)
arcpy.Delete_management("f_l")

celkem_segmentu_mimo = 0
celkem_koridoru_mimo = 0

for zpr_linka in linky_list:
    arcpy.MakeFeatureLayer_management("linky_cele.shp", "f_l")
    arcpy.SelectLayerByAttribute_management("f_l", "NEW_SELECTION", f"LINKA = {zpr_linka}")
    arcpy.CopyFeatures_management("f_l", "vybrana_linka.shp")

    arcpy.MakeFeatureLayer_management("MHDMost102023.shp", "f_l")
    arcpy.SelectLayerByAttribute_management("f_l", "NEW_SELECTION", f"CISLO_LINK = {zpr_linka}")
    arcpy.CopyFeatures_management("f_l", "vybrane_body.shp")

    arcpy.PairwiseBuffer_analysis("vybrane_body.shp", "buffer15.shp", 15)
    arcpy.PairwiseDissolve_analysis("buffer15.shp", f"koridor_linky_{zpr_linka}_15.shp")

    arcpy.PairwiseBuffer_analysis(f"koridor_linky_{zpr_linka}_15.shp", f"koridor_linky_{zpr_linka}_buffer_navic.shp", 75)
    arcpy.PairwiseBuffer_analysis(f"koridor_linky_{zpr_linka}_buffer_navic.shp", f"koridor_linky_{zpr_linka}.shp", -75)

    arcpy.Delete_management("buffer15.shp")
    arcpy.Delete_management(f"koridor_linky_{zpr_linka}_15.shp")

    # Následuje porovnání vytvořeného koridoru linky s linií linky
    arcpy.PairwiseErase_analysis(
        in_features="vybrana_linka.shp",
        erase_features=f"koridor_linky_{zpr_linka}.shp",
        out_feature_class=f"linka_{zpr_linka}_mimo.shp",
    )

    arcpy.management.FeatureToLine(
        in_features=f"linka_{zpr_linka}_mimo.shp",
        out_feature_class=f"useky_mimo_{zpr_linka}.shp",
        attributes="ATTRIBUTES"
    )

    sCur = arcpy.da.SearchCursor(f"useky_mimo_{zpr_linka}.shp", ["SHAPE@LENGTH", "SHAPE@XY"])

    output_file_path = r"D:\Zatka\output_linka_mimo.txt"

    with open(output_file_path, "a") as output_file:
        output_file.write(f"Očekávaná trasa linky {zpr_linka} neodpovídá zaznamenaným polohám v úsecích:\n")
        i = 0
        for sRow in sCur:
            poloha = sRow[1]
            delka = round(sRow[0], 1)
            if delka > 150:
                line_info = f"Linka {zpr_linka}; úsek délky {delka} m; pozice: {poloha}\n"
                output_file.write(line_info)
                print(line_info)
                celkem_segmentu_mimo += 1
                i += 1

        output_file.write(f"Celkem {i} úseků.\n")

    print(f"Data byla zapsána do souboru: {output_file_path}")

    del sCur

    # Následuje opačné porovnání - linka s vyvořeným koridorem
    arcpy.PairwiseBuffer_analysis("vybrana_linka.shp", f"linka_{zpr_linka}_buffer.shp", 150)
    arcpy.PairwiseErase_analysis(
        in_features=f"koridor_linky_{zpr_linka}.shp",
        erase_features=f"linka_{zpr_linka}_buffer.shp",
        out_feature_class=f"koridor_{zpr_linka}_mimo.shp",
    )

    arcpy.management.FeatureToPolygon(
    in_features=f"koridor_{zpr_linka}_mimo.shp",
    out_feature_class=f"kor_{zpr_linka}_mimo_ftpoly.shp")

    arcpy.CopyFeatures_management(f"kor_{zpr_linka}_mimo_ftpoly.shp", f"koridor_{zpr_linka}_mimo_FINAL.shp") #kopíruji do nového shp, abych mohl odstraňovat malé polygony, ale zároveň měl k dispozici i původní shp
    arcpy.DeleteFeatures_management(f"koridor_{zpr_linka}_mimo_FINAL.shp")

    sCur = arcpy.da.SearchCursor(f"kor_{zpr_linka}_mimo_ftpoly.shp", ["SHAPE@", "SHAPE@AREA"])
    iCur = arcpy.da.InsertCursor(f"koridor_{zpr_linka}_mimo_FINAL.shp", ["SHAPE@", "SHAPE@AREA"])

    for sRow in sCur:
        rozloha = sRow[1]
        if rozloha > 2000:
            iCur.insertRow((sRow))
            
    del sCur
    del iCur
    arcpy.CopyFeatures_management(f"koridor_{zpr_linka}_mimo_FINAL.shp", fr"D:\Zatka\detekce_chyb\detekce_chyb.gdb\koridor_{zpr_linka}_mimo_FINAL") 

    sCur = arcpy.da.SearchCursor(f"koridor_{zpr_linka}_mimo_FINAL.shp", ["SHAPE@AREA", "SHAPE@XY"])

    output_file_path_2 = r"D:\Zatka\output_koridor_mimo.txt"

    with open(output_file_path_2, "a") as output_file_2:
        output_file_2.write(f"Koridor naměřených bodů linky {zpr_linka} neodpovídá předpokládané trase linky v úsecích:\n")
        i = 0
        for sRow in sCur:
            i += 1
            poloha = sRow[1]
            velikost = round(sRow[0], 1)

            line_info = f"Linka {zpr_linka}; koridor velikosti {velikost} m2; pozice: {poloha}\n"
            output_file_2.write(line_info)
            print(line_info)
            celkem_koridoru_mimo += 1

        output_file_2.write(f"Celkem {i} úseků.\n")

    print(f"Data byla zapsána do souboru: {output_file_path_2}")

    del sCur

    arcpy.Delete_management("vybrana_linka.shp")
    arcpy.Delete_management("vybrane_body.shp")
    arcpy.Delete_management("f_l")
    arcpy.Delete_management(f"kor_{zpr_linka}_mimo_ftpoly_f_l")
    arcpy.Delete_management(f"koridor_{zpr_linka}_mimo.shp")
    arcpy.Delete_management(f"koridor_{zpr_linka}_mimo.shp")

    print(f"Celkem úseků mimo: {celkem_segmentu_mimo}, celkem koridorů mimo: {celkem_koridoru_mimo}")
    end_time = time.time()
    result_time = end_time - start_time
    print(f"Čas běhu programu: {result_time}")