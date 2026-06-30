from typing import Dict, List, Any


def build_dashboard_context(
    dados_fonte: List[Dict[str, Any]],
    dados_tema: List[Dict[str, Any]],
    dados_timeline: List[Dict[str, Any]],
    total_noticias: int,
) -> Dict[str, Any]:
    fontes_grafico = {item["fonte"]: item["total"] for item in dados_fonte}
    temas_grafico = {item["tema"]: item["total"] for item in dados_tema}
    timeline_labels = [item["dia"].strftime("%d/%m") for item in dados_timeline if item.get("dia")]
    timeline_values = [item["total"] for item in dados_timeline]

    return {
        "fontes_grafico": fontes_grafico,
        "temas_grafico": temas_grafico,
        "timeline_labels": timeline_labels,
        "timeline_values": timeline_values,
        "total_noticias": total_noticias,
        "fontes_disponiveis": list(fontes_grafico.keys()),
        "temas_disponiveis": list(temas_grafico.keys()),
    }
