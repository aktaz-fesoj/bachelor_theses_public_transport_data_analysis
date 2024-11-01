import arcpy
import statistics

arcpy.env.workspace = r"D:\Zatka\MostMHD_10_23_testy.gdb"
arcpy.env.overwriteOutput = 1
arcpy.env.qualifiedFieldNames = 0

delka_useku = 250
seznam_delek = []

def filtrace_bodu_dle_hodiny(body_shp, start, konec, vystup):
    arcpy.MakeFeatureLayer_management(body_shp, "fl_body")

    sql_podminka = f"EXTRACT(HOUR FROM TIME_DATE) >= {start} AND EXTRACT(HOUR FROM TIME_DATE) < {konec}"
    arcpy.SelectLayerByAttribute_management("fl_body", "NEW_SELECTION", sql_podminka)
    arcpy.CopyFeatures_management("fl_body", vystup)
    return(vystup)

start = 4
konec = 6
xid = 0

while konec < 25:
    seznam_delek = []

    #Přiřazení atributu o průměrném zpoždění jednotlivým segmentům linie
    body = filtrace_bodu_dle_hodiny("zaznamy_polohy", start, konec, "vybrane_body")
    linie_pred_rozsekanim = "linky_nekrizici_se"
    linie = f"linie_segment_{delka_useku}_{start}_{konec}"


    #rozsekat
    arcpy.MakeFeatureLayer_management(linie_pred_rozsekanim, 'input_layer')

    spatial_reference = arcpy.Describe(linie_pred_rozsekanim).spatialReference 

    arcpy.CreateFeatureclass_management(arcpy.env.workspace,linie,'POLYLINE',spatial_reference=spatial_reference)

    # vytvoření atributů - délka segmentu, průměrné zpoždění na daném segmentu - příprava k pozdějšímu naplnění daty, ID (z neznámého důvodu bez toho vhodně nefunguje následný spatial join)
    arcpy.AddField_management(linie, 'Segm_Len', 'DOUBLE')
    arcpy.AddField_management(in_table = linie, field_name = 'ZPOZ_PRUM', field_type = 'DOUBLE', field_alias = "průměrné zpoždění v úseku")
    arcpy.AddField_management(linie, 'ID_moje', 'INTEGER')


    with arcpy.da.InsertCursor(linie, ['SHAPE@', 'Segm_Len', 'ID_moje']) as insert_cursor:
        with arcpy.da.SearchCursor('input_layer', ['SHAPE@', 'SHAPE@LENGTH']) as search_cursor:
            for row in search_cursor:
                original_line = row[0]
                line_length = row[1]

                # kolik segmentů bude třeba aby byly všechny (krom posledního) dlouhé delka_useku metrů?
                num_segments = int(line_length / delka_useku)

                # rozsekání linie na segmenty
                for i in range(num_segments):
                    xid+=1
                    start_distance = i * delka_useku
                    end_distance = (i + 1) * delka_useku if i < num_segments - 1 else line_length

                    segment = original_line.segmentAlongLine(start_distance, end_distance)
                    segment_length = segment.length

                    # Vložení do výstupu
                    insert_cursor.insertRow([segment, segment_length, xid])

    arcpy.SpatialJoin_analysis(body, linie, 'body_linie_join', "#", "#", "#", "CLOSEST") # Spatial Join bodů a rozsekané linie

    zpozd_slovnik = {}  # slovník, do kterého budou ukládany body na základě nejbližšího segmentu linie linky

    with arcpy.da.SearchCursor('body_linie_join', ['ID_MOJE', 'ZPOZDENI_MIN']) as sCur: # SearchCursorem jsou procházeny body a zpoždění z nich ukládano do slovníku jako seznam ke každému ID segmentu
        for row in sCur:
            segment_id = row[0]
            zpozdeni = row[1]

            # Nový klíč dle segmentu, pokud zatím neexistuje
            if segment_id not in zpozd_slovnik:
                zpozd_slovnik[segment_id] = []

            zpozd_slovnik[segment_id].append(zpozdeni) # přidání hodnoty zpoždění do seznamu

    with arcpy.da.UpdateCursor(linie, ['ID_MOJE', 'ZPOZ_PRUM']) as uCur: # UpdateCursor prochází geometrii segmentů
        for row in uCur:
            segment_id = row[0]

            # pokud je ID segmentu nalezeno jako klíč ve slovníku uložených zpoždění, je vypočítán průměr zpoždění a jeho hodnota uložena do atributu ZPOZ_PRUM
            if segment_id in zpozd_slovnik:
                print(len(zpozd_slovnik[segment_id]))
                seznam_delek.append(len(zpozd_slovnik[segment_id]))
                prumer_zpoz = statistics.mean(zpozd_slovnik[segment_id])
                row[1] = prumer_zpoz
                uCur.updateRow(row)

    print(f"{start}-{konec}")
    print(statistics.mean(seznam_delek))
    print(min(seznam_delek))
    # vyčistění
    arcpy.Delete_management('input_layer')
    arcpy.Delete_management('vybrane_body')
    start += 2
    konec += 2
arcpy.Delete_management('body_linie_join')