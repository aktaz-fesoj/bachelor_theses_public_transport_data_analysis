import arcpy
import os
import statistics
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk

tato_slozka = os.path.dirname(os.path.realpath(__file__))
arcpy.env.workspace = rf"{tato_slozka}\MhdMost"
arcpy.env.overwriteOutput = 1
arcpy.env.qualifiedFieldNames = 0

project_path = rf"{tato_slozka}\project_aprx_mapy\project_most.aprx"
vysledky_slozka = rf"{tato_slozka}\vysledky"
uloziste_vrstev_slozka = rf"{tato_slozka}\vzory_lyrx"

def filtrace_bodu_cas(body_shp, start, konec, dny, vystup):
    arcpy.MakeFeatureLayer_management(body_shp, "fl_body")
    arcpy.CopyFeatures_management("fl_body", "fl_body_dny")
    arcpy.DeleteFeatures_management("fl_body_dny")
    sql_podminka = f"EXTRACT(HOUR FROM TIME_DATE) >= {start} AND EXTRACT(HOUR FROM TIME_DATE) < {konec}"
    arcpy.SelectLayerByAttribute_management("fl_body", "NEW_SELECTION", sql_podminka)
    with arcpy.da.InsertCursor("fl_body_dny", "*") as insert_cursor:
        with arcpy.da.SearchCursor("fl_body", "*") as search_cursor:
            for row in search_cursor:
                datum = row[12]
                vse = row
                if datum.weekday() in dny:
                    insert_cursor.insertRow(vse)
    arcpy.CopyFeatures_management("fl_body_dny", vystup)
    return(vystup)

def filtrace_linky(vstup, zpr_linka, vystup):
    arcpy.MakeFeatureLayer_management(vstup, "fl_body")
    # definování výběrové podmínky
    query_expression = f"CISLO_LINKY = {zpr_linka}"
    arcpy.SelectLayerByAttribute_management("fl_body", "NEW_SELECTION", query_expression)
    arcpy.CopyFeatures_management("fl_body", vystup)
    return(vystup)

def toggle_time_entries():
    if vybrat_hodiny.get() == 1:  # If the checkbox is checked
        start_label.grid(row=4, column=0, sticky='w')
        start_menu.grid(row=4, column=1, sticky='w')
        konec_label.grid(row=5, column=0, sticky='w')
        konec_menu.grid(row=5, column=1, sticky='w')
    else:
        start_label.grid_forget()
        start_menu.grid_forget()
        konec_label.grid_forget()
        konec_menu.grid_forget()
 
def submit():
    try:
        global delka_useku, zpr_linka, start, konec, dny
        delka_useku_str = delka_useku_entry.get()  # Get the input as string
        if not delka_useku_str:  # Check if input is empty
            raise ValueError("Empty input")  # Raise an error for empty input
        delka_useku = int(delka_useku_str)
        if delka_useku <= 0:
            raise Exception
        zpr_linka = int(zpr_linka_var.get())
        if vybrat_hodiny.get() == 1:
            start = int(start_var.get()[:2])
            konec = int(konec_var.get()[:2])
        else:
            start = 0
            konec = 25
        if start >= konec:
            raise Exception
        dny=[]
        dny_tf = [var.get() for var in day_vars]
        i = 0
        for tf in dny_tf:
            if tf == 1:
                dny.append(i)
            i+=1
        root.destroy()
        beh_programu(delka_useku, zpr_linka, start, konec, dny)
    except ValueError as ve:
        if str(ve) == "Empty input":
            messagebox.showwarning("Chybné zadání", "Délka segmentu musí být zadána.")
        else:
            messagebox.showwarning("Chybné zadání", "Něco je špatně se vstupem: {}".format(str(ve)))
    except Exception as e:
        messagebox.showwarning("Chybné zadání", e)

def hlaska():
    if delka_useku < 1:
        return("Délka segmentu musí být větší než 0.")
    if start >= konec:
        return("Čas začátku sledovaného období je zadán později než konec sledovaného období.")
    return("Zkontrolujte zadané veličiny.")

def beh_programu(delka_useku, zpr_linka, start, konec, dny):
    xid = 0
    vstup = 'MhdMost.gdb\zpolohy_zkontrolovano'
    body_vybrana_linka = filtrace_linky(vstup, zpr_linka, r'MhdMost.gdb\body_vybrana_linka')
    fc_body = filtrace_bodu_cas(body_vybrana_linka, start, konec, dny, r"MhdMost.gdb\fc_body")


    #Výběr konkrétní linky a uložení její trasy do vybrana_linka.shp
    #_________________________________________________________________

    linky_cele = 'MhdMost.gdb\linky_cele'
    feature_layer = "selected_features"
    arcpy.MakeFeatureLayer_management(linky_cele, feature_layer)

    query_expression = f"LINKA = {zpr_linka}"

    # definování výběrové podmínky
    arcpy.SelectLayerByAttribute_management(feature_layer, "NEW_SELECTION", query_expression)

    output_vyb_linka = 'vybrana_linka.shp'

    # nakopírování výběru do výsledného shapefilu
    arcpy.CopyFeatures_management(feature_layer, output_vyb_linka)
    arcpy.Delete_management(feature_layer)
    arcpy.management.Project(output_vyb_linka, 'vybrana_linka_proj.shp', 3857) #vytvoření stejné vrstvy v jiném zobrazení, aby bylo možné využít extent vrstvy pro zoomování finální mapy, ktreá je v souř. systému 3857 z důvodu podkladové mapy


    #Rozsekání dané linky po delka_useku metrech
    #_________________________________________________________________


    arcpy.MakeFeatureLayer_management("vybrana_linka.shp", 'input_layer')

    spatial_reference = arcpy.Describe("vybrana_linka.shp").spatialReference

    # Create the output shapefile
    arcpy.CreateFeatureclass_management(
        arcpy.env.workspace,
        "rozsekana_linka.shp",
        'POLYLINE',
        spatial_reference=spatial_reference
    )

    # vytvoření atributů - délka segmentu, průměrné zpoždění na daném segmentu - příprava k pozdějšímu naplnění daty, ID (z neznámého důvodu bez toho vhodně nefunguje následný spatial join)
    arcpy.AddField_management("rozsekana_linka.shp", 'Segm_Len', 'DOUBLE')
    arcpy.AddField_management(in_table = "rozsekana_linka.shp", field_name = 'Prum_Zpozd', field_type = 'DOUBLE', field_alias = "průměrné zpoždění v úseku")
    arcpy.AddField_management("rozsekana_linka.shp", 'ID_moje', 'INTEGER')


    with arcpy.da.InsertCursor("rozsekana_linka.shp", ['SHAPE@', 'Segm_Len', 'ID_moje']) as insert_cursor:
        with arcpy.da.SearchCursor('input_layer', ['SHAPE@', 'SHAPE@LENGTH']) as search_cursor:
            for row in search_cursor:
                original_line = row[0]
                line_length = row[1]

                # kolik segmentů bude třeba aby byly všechny (krom posledního) dlouhé delka_useku metrů?
                num_segments = int(line_length / delka_useku)

                # rozsekání linie na segmenty
                for i in range(num_segments):
                    xid +=1
                    start_distance = i * delka_useku
                    end_distance = (i + 1) * delka_useku if i < num_segments - 1 else line_length

                    segment = original_line.segmentAlongLine(start_distance, end_distance)
                    segment_length = segment.length

                    # Vložení do výstupu
                    insert_cursor.insertRow([segment, segment_length, xid])

    # vyčistění
    arcpy.Delete_management('input_layer')

    #Výběr zastávek
    #_________________________________________________________________
    zastavky_vyb = "selected_features"
    arcpy.MakeFeatureLayer_management("MhdMost.gdb\zastavky_jednotne", zastavky_vyb)

    query_expression = f"LINKY LIKE '{zpr_linka},%' OR LINKY LIKE '%, {zpr_linka},%' OR LINKY LIKE '%, {zpr_linka}' OR LINKY LIKE '{zpr_linka}'"

    # definování výběrové podmínky
    arcpy.SelectLayerByAttribute_management(zastavky_vyb, "NEW_SELECTION", query_expression)

    output_vyb_zastavky = 'vybrane_zastavky.shp'

    # nakopírování výběru do výsledného shapefilu
    arcpy.CopyFeatures_management(zastavky_vyb, output_vyb_zastavky)
    arcpy.Delete_management(zastavky_vyb)

    #Práce s body
    #______________________
    cilove_stanice = set()
    with arcpy.da.SearchCursor(fc_body, ["CILOVA_Z_1"]) as cursor:
        for row in cursor:
            attribute_value = row[0]
            cilove_stanice.add(attribute_value)

    body = 'vybrane_body.shp'
    for cilova_stanice in cilove_stanice:
        query_expression = f"CISLO_LINK = {zpr_linka}"
        arcpy.SelectLayerByAttribute_management(fc_body, "NEW_SELECTION", query_expression)
        query_expression2 = f"CILOVA_Z_1 = '{cilova_stanice}'"
        arcpy.SelectLayerByAttribute_management(fc_body, "SUBSET_SELECTION", query_expression2)
        # nakopírování výběru do výsledného shapefilu
        arcpy.CopyFeatures_management(fc_body, body)

        #Přiřazení atributu o průměrném zpoždění jednotlivým segmentům linie
        #_________________________________________________________________

        linie = 'rozsekana_linka.shp'

        # Spatial join bodů a rozsekané linie
        arcpy.SpatialJoin_analysis(body, linie, 'body_linie_join.shp', "#", "#", "#", "CLOSEST")

        # body budu ukládat do slovníku na základě nejbližšího segmentu linie linky
        point_dict = {}

        with arcpy.da.SearchCursor('body_linie_join.shp', ['TARGET_FID', 'ID_moje', 'ZPOZDENI_M']) as sCur:
            for row in sCur:
                point_id = row[0]
                line_id = row[1]
                attribute_value = row[2]

                # Nový klíč dle segmentu, pokud zatím neexistuje
                if line_id not in point_dict:
                    point_dict[line_id] = []

                point_dict[line_id].append(attribute_value)

        # Průměry z hodnot zpoždění, které jsou uloženy jako list hodnot u každého segmentu (který - jehož id - je klíčem slovníku)
        with arcpy.da.UpdateCursor(linie, ['ID_moje', 'Prum_Zpozd']) as uCur:
            for row in uCur:
                line_id = row[0]

                if line_id in point_dict:
                    average_value = statistics.mean(point_dict[line_id])
                    row[1] = average_value
                    uCur.updateRow(row)

        #Tvorba a export mapy
        #_________________________________________________________________


        aprx = arcpy.mp.ArcGISProject(project_path)

        aprxMap = aprx.listMaps()[0]
        for vrstva in aprxMap.listLayers():
            aprxMap.removeLayer(vrstva)

        arcpy.MakeFeatureLayer_management('vybrana_linka_proj.shp', "proj_extent")
        arcpy.MakeFeatureLayer_management("rozsekana_linka.shp", f"průměrné zpoždění v úsecích trasy linky {zpr_linka} (sekundy)")
        arcpy.MakeFeatureLayer_management("vybrane_zastavky.shp", "zastávky")
        arcpy.SaveToLayerFile_management("proj_extent", fr'{uloziste_vrstev_slozka}\proj_extent_layer.lyrx', "ABSOLUTE")
        arcpy.SaveToLayerFile_management(f"průměrné zpoždění v úsecích trasy linky {zpr_linka} (sekundy)", fr'{uloziste_vrstev_slozka}\rozsekana_linka_layer.lyrx', "ABSOLUTE")
        arcpy.SaveToLayerFile_management("zastávky", fr'{uloziste_vrstev_slozka}\vybrane_zastavky_layer.lyrx', "ABSOLUTE")

        aprxMap.addBasemap("Light Gray Canvas")
        aprxMap.addDataFromPath(fr'{uloziste_vrstev_slozka}\proj_extent_layer.lyrx')
        aprxMap.addDataFromPath(fr'{uloziste_vrstev_slozka}\rozsekana_linka_layer.lyrx')
        aprxMap.addDataFromPath(fr'{uloziste_vrstev_slozka}\vybrane_zastavky_layer.lyrx')

        extent_layer = aprxMap.listLayers()[2]
        extent_layer_symbology = fr"{uloziste_vrstev_slozka}\extent_layer_vzor.lyrx"
        trasa_linky_layer = aprxMap.listLayers()[1]
        trasa_linky_symbology = fr"{uloziste_vrstev_slozka}\rozsekana_linka_vzor.lyrx"
        zastavky_layer = aprxMap.listLayers()[0]
        zastavky_symbology = fr"{uloziste_vrstev_slozka}\vybrane_zastavky_vzor.lyrx"
        arcpy.ApplySymbologyFromLayer_management(trasa_linky_layer, trasa_linky_symbology)
        arcpy.ApplySymbologyFromLayer_management(zastavky_layer, zastavky_symbology)
        aprxMap.spatialReference = arcpy.SpatialReference(3857)

        
        # nastavení přizoomování na zpracovanou linku
        aprxLayout = aprx.listLayouts()[1]
        nadpis = aprxLayout.listElements("TEXT_ELEMENT", "Text 1")[0]
        nadpis.text = f"na lince {zpr_linka} ve směru {cilova_stanice}"
        map_frame = aprxLayout.listElements('MAPFRAME_ELEMENT', "Map Frame")[0]
        map_frame.camera.setExtent(map_frame.getLayerExtent(extent_layer, False, True))
        scale_cur = map_frame.camera.scale
        scale_new = scale_cur * 1.1
        map_frame.camera.scale = scale_new

        extent_layer.visible = False #použito pouze pro nastavení extentu

        symbology = trasa_linky_layer.symbology
        if hasattr(symbology, 'classList'):
            for legend_class in symbology.classList:
                print(legend_class)

        #export do pdf
        aprxLayout.exportToPDF(fr"{vysledky_slozka}\layout_{zpr_linka}_usek_{delka_useku}_smer_{cilova_stanice}")
        print(f"proběhlo pro směr {cilova_stanice}")
        del aprx
        for vrstva in aprxMap.listLayers():
            aprxMap.removeLayer(vrstva)
    
    im = Image.open(rf"{tato_slozka}\design\dyckymost.gif")
    window = tk.Tk()
    window.iconbitmap(rf"{tato_slozka}\design\busicon.ico")
    window.title("Mapy vygenerovány!")
    gif_frames = []
    try:
        while True:
            gif_frames.append(ImageTk.PhotoImage(im))
            im.seek(im.tell() + 1)
    except EOFError:
        pass
    label = tk.Label(window, image=gif_frames[0])
    label.pack()
    def animate(frame):
        label.configure(image=gif_frames[frame])
        window.after(100, animate, (frame + 1) % len(gif_frames))
    animate(1)
    messagebox.showinfo("Zpoždění Most", r"Mapy úspěšně vygenerovány. Uloženy v adresáři \vysledky")
    window.mainloop()
root = tk.Tk()
root.geometry("280x350")
root.iconbitmap(rf"{tato_slozka}\design\busicon.ico")
root.title("Zpoždění Most")

tk.Label(root, text="Délka segmentu (m):").grid(row=0, column=0, sticky='w')
delka_useku_entry = tk.Entry(root)
delka_useku_entry.grid(row=0, column=1)

tk.Label(root, text="Číslo linky:").grid(row=1, column=0, sticky='w')
zpr_linka_options = [1, 2, 3, 4, 5, 8, 9, 10, 12, 13, 14, 15, 16, 17, 18, 20, 21, 22, 23, 25, 27, 28, 30, 31, 40, 50, 51, 53, 60]
zpr_linka_var = tk.StringVar(root)
zpr_linka_var.set(zpr_linka_options[0])
zpr_linka_menu = tk.OptionMenu(root,zpr_linka_var, *zpr_linka_options)
zpr_linka_menu.grid(row=1, column=1, sticky='w')

tk.Label(root, text="Dny:").grid(row=5, column=0, sticky='w')

days_mapping = {
    "pondělí": 0,
    "úterý": 1,
    "středa": 2,
    "čtvrtek": 3,
    "pátek": 4,
    "sobota": 5,
    "neděle": 6
}

day_vars = []
for day_name, i in days_mapping.items():
    var = tk.IntVar()
    var.set(1)
    checkbutton = tk.Checkbutton(root, text=day_name, variable=var)
    checkbutton.grid(row=6+i, column=1, sticky='w')
    day_vars.append(var)

vybrat_hodiny = tk.IntVar()
checkbox_time = tk.Checkbutton(root, text="Vybrat rozmezí hodin", variable=vybrat_hodiny, command=toggle_time_entries)
checkbox_time.grid(row=2, column=1, sticky='w')

start_label = tk.Label(root, text="Počáteční čas intervalu:")
konec_label = tk.Label(root, text="Koncový čas intervalu:")
start_options = ["{:02d}:00".format(i) for i in range(25)]
start_var = tk.StringVar(root)
start_var.set(start_options[0])
start_menu = tk.OptionMenu(root, start_var, *start_options)


konec_options = ["{:02d}:00".format(i) for i in range(25)]
konec_var = tk.StringVar(root)
konec_var.set(konec_options[0])
konec_menu = tk.OptionMenu(root, konec_var, *konec_options)

submit_button = tk.Button(root, text="Vygenerovat mapu", command=submit)
submit_button.grid(row=13, columnspan=8)
root.mainloop()