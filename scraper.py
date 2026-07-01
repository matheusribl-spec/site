import hashlib
import logging
import re
from pathlib import Path
from time import perf_counter
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter, Retry
from requests.exceptions import RequestException, Timeout

import models
from config import Config

logger = logging.getLogger(__name__)

MAX_NEWS_PER_SOURCE = 5

SOURCE_LIST = [
    {"url": "https://g1.globo.com/politica/", "nome": "G1", "tema": "Política"},
    # {"url": "https://www.uol.com.br/politica/", "nome": "UOL", "tema": "Política"},
    # {"url": "https://www1.folha.uol.com.br/poder/", "nome": "Folha", "tema": "Política"},
    # {"url": "https://www.poder360.com.br/", "nome": "Poder360", "tema": "Política"},
    # {"url": "https://www.metropoles.com/politica/", "nome": "Metrópoles", "tema": "Política"},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

RELEVANT_KEYWORDS = [
    "eleição",
    "eleições",
    "eleitoral",
    "candidato",
    "candidatura",
    "voto",
    "urna",
    "campanha",
    "lei",
    "legislação",
    "pl",
    "pec",
    "projeto de lei",
    "senado",
    "câmara",
    "parlamento",
    "governo",
    "ministro",
    "ministra",
    "parlamentar",
    "deputado",
    "senador",
    "vereador",
    "bancada",
    "política",
    "políticas públicas",
    "saúde",
    "educação",
    "infraestrutura",
    "saneamento",
    "assistência",
    "direito",
    "supremo",
    "stf",
    "cpi",
    "congresso",
    "trâmite",
    "legislativo",
    "judiciário",
    "eleitor",
]

UNWANTED_LINK_SEGMENTS = [
    "/sobre",
    "/projeto",
    "/equipe",
    "/contato",
    "/marketing",
    "/politica-de-privacidade",
    "/termos",
    "/cookies",
    "/metodologia",
    "/carreira",
    "/servicos",
    "/guia",
    "/newsletter",
    "/agenda",
    "/evento",
    "/eventos",
    "/colunistas",
    "/coluna",
    "/podcast",
    "/podcasts",
    "/para-voce",
    "/publicidade",
    "/assinatura",
    "/maps",
    "/anuncie",
    "/parcerias",
]

UNWANTED_TITLE_PATTERNS = [
    "o projeto consiste",
    "ecossistema digital",
    "desenvolvimento de",
    "metodologia ágil",
    "controle do código-fonte",
    "github",
    "cronograma",
    "sprints",
    "gestão de tarefas",
    "ferramenta de apoio",
    "plataforma integrada",
    "notificações configuradas",
    "aplicação mobile",
    "aplicação web",
    "dashboard analítico",
    "gestão do projeto",
    "fase de planejamento",
    "implantação em ambiente",
    "repositório no github",
]

NEWS_IMAGE_FOLDER = Path(Config.UPLOAD_FOLDER) / "news"


def _create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
        backoff_factor=1,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _is_title_relevant(text: str) -> bool:
    normalized = text.lower()
    if any(pattern in normalized for pattern in UNWANTED_TITLE_PATTERNS):
        return False
    return any(keyword in normalized for keyword in RELEVANT_KEYWORDS)


def _is_link_relevant(link: str) -> bool:
    normalized = link.lower()
    return not any(segment in normalized for segment in UNWANTED_LINK_SEGMENTS)


def _classify_topic(title: str, default_topic: str) -> str:
    text = title.lower()
    eleicoes = ["eleição", "eleições", "candidato", "candidatura", "voto", "urna", "campanha"]
    legislacao = ["lei", "legislação", "pl", "pec", "projeto de lei", "câmara", "senado", "parlamento", "comissão"]
    politicas_publicas = ["política pública", "políticas públicas", "ministro", "governo", "saúde", "educação", "infraestrutura", "saneamento", "assistência"]
    parlamentares = ["parlamentar", "deputado", "senador", "vereador", "bancada"]

    if any(item in text for item in eleicoes):
        return "Eleições"
    if any(item in text for item in legislacao):
        return "Legislação"
    if any(item in text for item in politicas_publicas):
        return "Políticas Públicas"
    if any(item in text for item in parlamentares):
        return "Parlamentares"

    return default_topic or "Política"


def _fetch_response(url: str, session: requests.Session) -> Optional[requests.Response]:
    try:
        response = session.get(url, timeout=Config.SCRAPER_TIMEOUT, allow_redirects=True)
        if response.status_code == 403:
            logger.warning("403 em %s, usando UA alternativa", url)
            alt_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0",
                "Referer": "https://www.google.com/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "pt-BR,pt;q=0.9",
            }
            response = session.get(url, headers=alt_headers, timeout=Config.SCRAPER_TIMEOUT, allow_redirects=True)
        if response.status_code == 404:
            root = re.match(r"(https?://[^/]+)", url)
            if root:
                root_url = root.group(1)
                logger.warning("404 em %s, tentando %s", url, root_url)
                response = session.get(root_url, timeout=Config.SCRAPER_TIMEOUT, allow_redirects=True)
        response.raise_for_status()
        return response
    except (RequestException, Timeout) as exception:
        logger.warning("Falha ao acessar %s: %s", url, exception)
        return None


def _sanitize_filename(url: str) -> str:
    parsed = urlparse(url)
    base_name = Path(parsed.path).name or "noticia"
    sanitized_base = re.sub(r"[^a-zA-Z0-9_.-]", "_", base_name)
    suffix = Path(sanitized_base).suffix or ".jpg"
    hash_fragment = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
    return f"{hash_fragment}{suffix}"


def _ensure_news_image_folder() -> Path:
    NEWS_IMAGE_FOLDER.mkdir(parents=True, exist_ok=True)
    return NEWS_IMAGE_FOLDER


def _save_image(image_url: str, session: requests.Session) -> Optional[str]:
    response = _fetch_response(image_url, session)
    if not response:
        return None

    content_type = response.headers.get("Content-Type", "")
    if not content_type.startswith("image"):
        return None

    folder = _ensure_news_image_folder()
    filename = _sanitize_filename(image_url)
    destination = folder / filename

    try:
        with destination.open("wb") as handle:
            handle.write(response.content)
        return str(Path("uploads") / "news" / filename).replace("\\", "/")
    except OSError as exception:
        logger.warning("Falha ao salvar imagem %s: %s", image_url, exception)
        return None


def _extract_image(link: str, session: requests.Session) -> Optional[str]:
    # Temporariamente desabilitado para reduzir a duração do scraping.
    return None


def _gather_links(source: Dict[str, str], session: requests.Session, seen_links: Set[str]) -> List[Dict[str, str]]:
    response = _fetch_response(source["url"], session)
    if not response:
        return []

    document = BeautifulSoup(response.text, "html.parser")
    results: List[Dict[str, str]] = []

    for anchor in document.select("a[href]"):
        if len(results) >= MAX_NEWS_PER_SOURCE:
            break

        title = anchor.get_text(strip=True)
        raw_link = anchor["href"].strip()
        link = urljoin(source["url"], raw_link)

        if not title or len(title) < 40:
            continue
        if not link.startswith("http"):
            continue
        if link in seen_links:
            continue
        if any(fragment in link for fragment in ["/autor/", "/tag/", "/videos/", "#"]):
            continue
        if not _is_link_relevant(link):
            continue
        if not _is_title_relevant(title):
            continue

        image_path = None
        results.append(
            {
                "tema": _classify_topic(title, source["tema"]),
                "manchete": title.strip(),
                "link": link,
                "fonte": source["nome"],
                "image": image_path,
            }
        )
        seen_links.add(link)

    return results


def scrape_news() -> List[Dict[str, Optional[str]]]:
    session = _create_session()
    collected: List[Dict[str, Optional[str]]] = []
    seen_links: Set[str] = set()

    start_total = perf_counter()

    for source in SOURCE_LIST:
        source_name = source["nome"]
        logger.info("Iniciando scraping do %s...", source_name)
        start_source = perf_counter()
        collected_source = _gather_links(source, session, seen_links)
        collected.extend(collected_source)
        source_elapsed = perf_counter() - start_source
        logger.info("%s concluído em %.2f segundos", source_name, source_elapsed)
        logger.info("Foram coletadas %d notícias do %s", len(collected_source), source_name)

    total_elapsed = perf_counter() - start_total
    logger.info("Tempo total de scraping: %.2f segundos", total_elapsed)

    return collected


def update_news() -> int:
    """Execute scraping e grave novas notícias no banco."""
    noticias = scrape_news()
    return models.save_news_items(noticias)
