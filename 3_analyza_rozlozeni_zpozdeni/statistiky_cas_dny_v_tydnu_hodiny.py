import arcpy
import statistics
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import make_interp_spline

arcpy.env.workspace = r"D:\Zatka\MostMHD_10_23.gdb"
arcpy.env.overwriteOutput = 1
arcpy.env.qualifiedFieldNames = 0

def filtrace_bodu_dle_hodiny_dni(body_shp, start, konec, den, vystup):
    list_zpozdeni = []

    arcpy.MakeFeatureLayer_management(body_shp, "fl_body")
    sql_podminka = f"EXTRACT(HOUR FROM TIME_DATE) >= {start} AND EXTRACT(HOUR FROM TIME_DATE) < {konec}"
    arcpy.SelectLayerByAttribute_management("fl_body", "NEW_SELECTION", sql_podminka)
    with arcpy.da.SearchCursor("fl_body", ["ZPOZDENI_MIN","TIME_DATE"]) as search_cursor:
        for row in search_cursor:
            zpozdeni = row[0]
            datum = row[1]
            if datum.weekday() == den:
                list_zpozdeni.append(zpozdeni)
    arcpy.CopyFeatures_management("fl_body", vystup)
    print(len(list_zpozdeni))
    if len(list_zpozdeni) != 0:
        return(statistics.mean(list_zpozdeni))
    else:
        return(0)

dict_dny = {}
for den in [0,1,2,3,4,5,6]:
    st = 4
    ko = 5
    zpozd_slov_hodiny = {}
    while ko < 25:
        zpozdeni = filtrace_bodu_dle_hodiny_dni(r"zaznamy_polohy", st, ko, den, "vybrane_body.shp")
        print(f"{st}:{zpozdeni}")
        zpozd_slov_hodiny.update({(st):zpozdeni*60})
        st+=1
        ko+=1
    dict_dny.update({den:zpozd_slov_hodiny})

print(dict_dny)

mean_data = {}
for hour in range(4, 24):
    hourly_data = [dict_dny[day][hour] for day in range(7)]
    mean_data[hour] = np.mean(hourly_data)
mean_x_values = list(mean_data.keys())
mean_y_values = list(mean_data.values())

plt.figure(figsize=(8.27, 11))
i = 1

for label, line_data in dict_dny.items():
    x_values = list(line_data.keys())
    y_values = list(line_data.values())
    if label == 0:
        den_slovy = "pondělí"
    elif label == 1:
        den_slovy = "úterý"
    elif label == 2:
        den_slovy = "středa"
    elif label == 3:
        den_slovy = "čtvrtek"
    elif label == 4:
        den_slovy = "pátek"
    elif label == 5:
        den_slovy = "sobota"
    elif label == 6:
        den_slovy = "neděle"

    plt.subplot(4,2, i)  # tvořím subploty do mřížky 2x4
    plt.plot(x_values, y_values)
    plt.plot(mean_x_values, mean_y_values, color='grey', linestyle='--', label='průměr všech dní')
    plt.title(den_slovy)
    plt.xlabel('hodina')
    plt.ylabel('průměrné zpoždění (sekundy)')
    plt.xticks(np.arange(4, 24, step=2), np.arange(4, 24, step=2))
    plt.yticks(np.arange(-10, 71, step=10)) 
    plt.grid(True)
    plt.grid(True, which='both')
    plt.legend()
    i += 1

# osmý plot pro průměr všech dní
plt.subplot(4, 2, i)
plt.plot(mean_x_values, mean_y_values, color='red')
plt.title('průměr všech dní')
plt.xlabel('hodina')
plt.ylabel('průměrné zpoždění (sekundy)')
plt.xticks(np.arange(4, 24, step=2), np.arange(4, 24, step=2))
plt.yticks(np.arange(-10, 71, step=10))  # Set yticks range from -10 to 70
plt.grid(True)
plt.grid(True, which='both')

plt.tight_layout()  # Adjust layout to prevent overlapping
plt.savefig(r"D:\Zatka\fig_zk_svg.svg")