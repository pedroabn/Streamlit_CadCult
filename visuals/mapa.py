# visuals/mapa.py
import folium
from folium.plugins import MarkerCluster, MiniMap, GroupedLayerControl
import branca.colormap as cm
import pandas as pd

def display_mapa(df_area, dfb, df_t):
    recife_coords = [-8.05428, -34.88126]
    m = folium.Map(location=recife_coords, zoom_start=13, tiles="Cartodb dark_matter")

    marker_cluster = MarkerCluster(name="Cadastros totais", show=True).add_to(m)
    MiniMap(toggle_display=True).add_to(m)

    linear = cm.linear.Oranges_06.scale(0, 20)
    linear.add_to(m)

    # Resumo por bairro
    fgpb = folium.FeatureGroup(name="Resumo por Bairro", show=True)

    folium.GeoJson(
        dfb,
        name="Bairros",
        style_function=lambda f: {
            "color": "black",
            "weight": 0.5,
            "fillOpacity": 0.1,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["EBAIRRNOMEOF", "inscritos", "total_pessoas"],
            aliases=["Bairro:", "Inscritos:", "Total Pessoas:"],
        ),
    ).add_to(fgpb)
    m.add_child(fgpb)

    # Cluster geral
    for row in df_area.itertuples():
        popup = folium.Popup(
            f"Genero: {row.genero} \n Raça: {row.raca} \n Estilo: {row.area_atuacao}",
            parse_html=True,
            max_width="100",
        )
        folium.Circle(
            location=(row.latitude, row.longitude),
            radius=10,
            fill_color="green",
            fill_opacity=0.4,
            color="white",
            popup=popup,
        ).add_to(marker_cluster)

    # Por grupo selecionado (áreas de atuação)
    grupos_area = {}
    areas_unicas = df_area["area_atuacao"].dropna().unique()
    for area in areas_unicas:
        fcad = folium.FeatureGroup(name=area, show=False)
        cluster = MarkerCluster().add_to(fcad)
        df_area_unica = df_area[df_area["area_atuacao"] == area]
        for _, row in df_area_unica.iterrows():
            location = (row.latitude, row.longitude)
            popup_textl = folium.Popup(
                f"Genero: {row.genero} \n Raça: {row.raca} \n Estilo: {row.area_atuacao}",
                parse_html=True,
                max_width="100",
            )
            folium.Circle(
                location=location,
                popup=popup_textl,
                radius=10,
                fill_color="white",
                fill_opacity=1,
                color="black",
                weight=1,
            ).add_to(cluster)
        grupos_area[area] = fcad
        m.add_child(fcad)

    # Teatros
    fgt = folium.FeatureGroup(name="Teatro", show=True)
    for row in df_t.itertuples():
        location_e = (row.latitude, row.longitude)
        popup_textep = folium.Popup(
            f"Nome: {row.equipamento}  \n Tipo: {row.tipo} \n Natureza: {row.natureza}",
            parse_html=True,
            max_width="100%",
        )
        folium.Marker(
            location=location_e,
            popup=popup_textep,
            tooltip=row.equipamento,
        ).add_to(fgt)
    fgt.add_to(m)

    GroupedLayerControl(
        exclusive_groups=False,
        groups={"Individuais": [fgt], "Por Bairro": [fgpb]},
        collapsed=False,
    ).add_to(m)

    GroupedLayerControl(
        exclusive_groups=False,
        groups={
            "Total": [marker_cluster],
            "Por Área de Atuação": list(grupos_area.values()),
        },
        collapsed=False,
        position="topleft",
    ).add_to(m)

    return m
