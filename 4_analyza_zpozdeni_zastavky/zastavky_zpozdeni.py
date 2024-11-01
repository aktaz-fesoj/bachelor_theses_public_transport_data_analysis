import arcpy
from collections import Counter
import csv

arcpy.env.workspace = r"D:\Zatka\MostMHD_10_23.gdb"
workspace = r"D:\Zatka\MostMHD_10_23.gdb"
arcpy.env.overwriteOutput = 1
arcpy.env.qualifiedFieldNames = 0

seznam_special = []

def kolmice(point1, point2): # vytváří kolmou linii z dvou bodů
    dx = point2.X - point1.X
    dy = point2.Y - point1.Y

    # pro kolmý vektor je nutné u jedné souřadnice prohodit znaménko
    kolm_dx = -dy/2
    kolm_dy = dx/2

    #souřadnice středu původní úsečky
    mid_x = (point1.X + point2.X) / 2
    mid_y = (point1.Y + point2.Y) / 2

    zacatek = arcpy.Point(mid_x + kolm_dx, mid_y + kolm_dy)
    konec = arcpy.Point(mid_x - kolm_dx, mid_y - kolm_dy)
    body_vysl = arcpy.Array()
    body_vysl.add(zacatek)
    body_vysl.add(konec)
    return body_vysl


linky_set = set()

arcpy.MakeFeatureLayer_management("linky", "f_l")
with arcpy.da.SearchCursor("f_l", "LINKA") as cursor:
    for row in cursor:
        linky_set.add(row[0])

for zpr_linka in linky_set:
    podm = f"LINKY LIKE '{zpr_linka},%' OR LINKY LIKE '%, {zpr_linka},%' OR LINKY LIKE '%, {zpr_linka}' OR LINKY LIKE '{zpr_linka}'"
    arcpy.MakeFeatureLayer_management("zastavky", "zastavky_fl", podm)
    arcpy.MakeFeatureLayer_management("linky", "linka_fl", f"LINKA = {zpr_linka}")
    arcpy.Buffer_analysis("zastavky_fl", "zastavky_buffer_100", 100)
    arcpy.AddField_management("zastavky_buffer_100", "konecna", "INTEGER")

    arcpy.CreateFeatureclass_management(workspace, 'pruniky', 'POINT', spatial_reference="zastavky_buffer_100")
    arcpy.CreateFeatureclass_management(workspace, 'kolmice', 'POLYLINE', spatial_reference="zastavky_buffer_100")
    arcpy.CreateFeatureclass_management(workspace, "specialni_polygony", 'POLYGON', spatial_reference="zastavky_buffer_100")
    arcpy.AddField_management("kolmice", "nazev_zastavky", "STRING")
    arcpy.AddField_management("specialni_polygony", "nazev_zastavky", "STRING")

    arcpy.management.MakeTableView("linky", "vybrana_linka_fc", f"LINKA = {zpr_linka}")
    with arcpy.da.SearchCursor("vybrana_linka_fc", ["SHAPE@"]) as cursor:
        for row in cursor:
            line_geom = row[0]

    with arcpy.da.SearchCursor("zastavky_buffer_100", ['SHAPE@']) as cursor:
        with arcpy.da.InsertCursor("pruniky", ['SHAPE@XY']) as insert_cursor:
            for row in cursor:
                polygon = row[0]
                hranice_pol = polygon.boundary()
                intersection = hranice_pol.intersect(line_geom, 1)
                if intersection and len(intersection) > 0:  #pokud existuje, bude bod či body průsečíků uloženy do tabulky pruniky
                    for point in intersection:
                        insert_cursor.insertRow([(point.X, point.Y)])

    with arcpy.da.SearchCursor("zastavky_buffer_100", ['SHAPE@', "NAZEV"]) as cursor:
        with arcpy.da.InsertCursor("kolmice", ['SHAPE@', "nazev_zastavky"]) as insert_cursor_kolmice:
            for row in cursor:
                polygon = row[0]
                hranice_pol = polygon.boundary()
                envelope = polygon.extent
                stred_polygonu = polygon.centroid
                intersection = hranice_pol.intersect(line_geom, 1)
                if intersection and len(intersection) == 2:         #existují-li právě dva průsečíky, jde o nejběžnější případ
                    array = arcpy.Array()
                    for point in intersection:
                        array.add(arcpy.Point(point.X, point.Y))
                    body_vysl = kolmice(array[0], array[1])             #k bodům je předem definovanou fcí vytvořena kolmá úsečka
                    spatial_ref = arcpy.Describe("zastavky_buffer_100").spatialReference
                    linie_kolmice = arcpy.Polyline(body_vysl, spatial_ref)
                    insert_cursor_kolmice.insertRow([linie_kolmice, row[1]])
                if intersection and len(intersection) > 2:          #existují-li více než 2 průsečíky, jsou uloženy do speciálního seznamu
                    seznam_special.append([zpr_linka, row[1]])

    with arcpy.da.UpdateCursor("zastavky_buffer_100", ['SHAPE@', "konecna"]) as cursor:
        for row in cursor:
            polygon = row[0]
            konecna = row[1]
            hranice_pol = polygon.boundary()
            intersection = hranice_pol.intersect(line_geom, 1)
            if len(intersection) == 1:              #existuje-li právě jeden průsečík, jde (pokud se nejedná o chybu) o konečnou zastávku
                cursor.updateRow([row[0], 1])       #informace o konečnosti je poté uložena do atributu konecna
            else:
                cursor.updateRow([row[0], 0])

    for zaz in seznam_special:
        if zaz[0] == zpr_linka: #je-li buffer ve speciálním seznamu, znamená to, že byly nalezeny více než 2 průsečíky hranice bufferu a linie linky
            nzv = zaz[1]
            arcpy.SelectLayerByAttribute_management("zastavky_fl", "NEW_SELECTION", f"NAZEV = '{nzv}'")
            arcpy.Buffer_analysis("zastavky_fl", "zastavka_spec_buffer", 200)                                 
            arcpy.analysis.Intersect(["zastavka_spec_buffer", "linka_fl"], "usek_linie_specialni")          #linie linky je oseknuta dle bufferu 200 m od zastávky
            arcpy.SplitLineAtPoint_management("usek_linie_specialni", "zastavky_fl", "rozdelene_linie", 30) 
            arcpy.Buffer_analysis("rozdelene_linie", "rozdelene_linie_buffer", 30, line_end_type="FLAT")    #vzniklá linie rozdělena bodem zastávky, pak obě části obaleny bufferem -> oba příjezdové směry mají svůj polygon
            arcpy.RemoveOverlapMultiple_analysis("rozdelene_linie_buffer", "vysledne_spec_polygony")

            #vložení názvu zastávky ke speciálnímu polygonu zóny zastávky
            with arcpy.da.SearchCursor("vysledne_spec_polygony", ['SHAPE@', "NAZEV"]) as cursor:
                with arcpy.da.InsertCursor("specialni_polygony", ['SHAPE@', "nazev_zastavky"]) as insert_cursor:
                    for row in cursor:
                        insert_cursor.insertRow([row[0], row[1]])

    #levostranný a pravostranný buffer
    arcpy.Buffer_analysis("kolmice", "zony_zastavky_1", 225, "LEFT", "FLAT")
    arcpy.Buffer_analysis("kolmice", "zony_zastavky_2", 225, "RIGHT", "FLAT")

    arcpy.MakeFeatureLayer_management("zastavky_buffer_100", "konecne_zastavky_buffer_fl", "konecna = 1") # vybrány zónyy konečných zastávek
    arcpy.CopyFeatures_management("konecne_zastavky_buffer_fl", "konecne_zastavky_buffer")

    #spojení polygonů zóny zastávky všech možných původů (tj. standardních od kolmice na linku, polygonů konečných zastávek a víceprůnikových případů)
    arcpy.Merge_management(["zony_zastavky_1", "zony_zastavky_2", "konecne_zastavky_buffer", "specialni_polygony"], f"zony_zastavek_s_overlap_{zpr_linka}", add_source = "ADD_SOURCE_INFO")
    arcpy.RemoveOverlapMultiple_analysis(f"zony_zastavek_s_overlap_{zpr_linka}", f"zony_zastavek_{zpr_linka}")

    arcpy.MakeFeatureLayer_management("zaznamy_polohy", "zaznamy_polohy_vybrano", f"CISLO_LINKY = {zpr_linka}") #výběr záznamů bodů dané linky

    #obohacení záznamů bodů polohy o zónu zastávky ve které leží
    arcpy.SpatialJoin_analysis("zaznamy_polohy_vybrano", f"zony_zastavek_{zpr_linka}", "zaznamy_polohy_spatial_join")

    arcpy.MakeFeatureLayer_management("zaznamy_polohy_spatial_join", "zaznamy_polohy_fl", "ORIG_FID IS NOT NULL")
    arcpy.CopyFeatures_management("zaznamy_polohy_fl","kontrola")
    seznam_oid = []
    with arcpy.da.SearchCursor(f"zony_zastavek_{zpr_linka}", ["OID@", "SHAPE@"]) as cursor:
        for polygon in cursor:
            polygon_oid = polygon[0]
            polygon_shape = polygon[1]

            nazev = f"zaznamy_polygon_{polygon_oid}"

            if polygon_shape != None:
                arcpy.SelectLayerByLocation_management("zaznamy_polohy_fl", "INTERSECT", polygon_shape)
                arcpy.CopyFeatures_management("zaznamy_polohy_fl", nazev)   #vytvořena feature class bodů ležících ve zpracovávaném polygonu pod specifickým názvem -> nebude přepsána další iterací

                seznam_oid.append(polygon_oid)

    slovnik_zon_zastavek = {}
    for polygon_oid in seznam_oid:
        fc = f"zaznamy_polygon_{polygon_oid}"

        value_counts = Counter()
        i = 0
        with arcpy.da.SearchCursor(fc, ["POSLEDNI_ZASTAVKA_NAME", "NAZEV", "nazev_zastavky"]) as cursor:
            for row in cursor:
                if row[0] != row[1] and row[0] != row[2]:
                    value_counts[row[0]] += 1
                    i+=1
        if i > 0:
            nejcastejsi_zastavka, pocet_vyskytu = value_counts.most_common(1)[0]
            vvv = f"POSLEDNI_ZASTAVKA_NAME = '{nejcastejsi_zastavka}' AND CISLO_LINKY = {zpr_linka}"    #nejčastější poslední projetá zastávka slouží jako identifikátor směru, ze kterého spoje přijíždějí
            arcpy.MakeFeatureLayer_management(fc, "fc_vybrano", vvv)
            arcpy.CopyFeatures_management("fc_vybrano", "zaznamy_polygon_vybrano")
            arcpy.Delete_management(fc)

            soucet = 0
            pocet = 0

            with arcpy.da.SearchCursor("zaznamy_polygon_vybrano", ["ZPOZDENI_MIN", "POSLEDNI_ZASTAVKA_NAME"]) as cursor:
                for row in cursor:
                    if row[0] is not None:
                        soucet += row[0]
                        pocet += 1
            
            prumerne_zpozdeni = soucet/pocet

            slovnik_zon_zastavek[polygon_oid] = [nejcastejsi_zastavka, prumerne_zpozdeni]
        arcpy.Delete_management("zaznamy_polygon_vybrano")

    #do zón zastávek je uložena informace o nejčastější poslední zastávce (tzn. směru) a o průměrném zpoždění záznamů polohy dané linky ležících uvnitř polygonu
    arcpy.AddField_management(f"zony_zastavek_{zpr_linka}", "Posledni_zastavka", "String")
    arcpy.AddField_management(f"zony_zastavek_{zpr_linka}", "PrumerneZpozdeni", "Double")
    with arcpy.da.UpdateCursor(f"zony_zastavek_{zpr_linka}", ["OID@", "Posledni_zastavka", "PrumerneZpozdeni"]) as cursor:
        for row in cursor:
            klic = row[0]
            if klic in slovnik_zon_zastavek:
                row[1] = slovnik_zon_zastavek[klic][0]
                row[2] = slovnik_zon_zastavek[klic][1]
                cursor.updateRow(row)

#export do csv
    output_csv = r"D:\Zatka\zpozdeni_zastavky.csv"
    with arcpy.da.SearchCursor(f"zony_zastavek_{zpr_linka}", ["nazev_zastavky", "NAZEV", "Posledni_zastavka", "PrumerneZpozdeni"]) as cursor, open(output_csv, 'a', newline='') as file:
        csv_writer = csv.writer(file, delimiter = ";")
        for row in cursor:
            if row[0] == None:
                csv_writer.writerow([row[1], row[2], row[3], zpr_linka])
            else:
                csv_writer.writerow([row[0], row[2], row[3], zpr_linka])

    print(f"Zapsána linka {zpr_linka}.")