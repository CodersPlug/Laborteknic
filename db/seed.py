"""Initialize schema and seed agent knowledge for the Laborteknic slideshow."""

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent
DB = ROOT / "laborteknic.duckdb"
SCHEMA = ROOT / "schema.sql"

PROJECT = dict(
    id="laborteknic",
    display_name="Laborteknic — Presentación institucional",
    repo_path="/Users/leo/Documents/Projects/Laborteknic",
    repo_github="CodersPlug/Laborteknic",
    live_url="https://codersplug.github.io/Laborteknic/",
    deploy_branch="main",
    stack="Single-file HTML slideshow (index.html), CSS/JS embedded, assets/img self-hosted",
)

CONSTANTS = [
    ("THEME_BG", "theme-paper / #F5F8FA", "Fondo claro unificado en todas las diapos"),
    ("FONT_DISPLAY", "Poppins", "Títulos"),
    ("FONT_BODY", "Inter", "Cuerpo"),
    ("COLOR_BLUE", "#00AEEF", "Acento marca"),
    ("COLOR_BLUE_DARK", "#0077A8", "Acento oscuro / carteles"),
    ("PAGES_BRANCH", "main", "GitHub Pages source branch — push a main, no a master"),
    ("SLIDE_QUERY", "?slide=N", "Jump 0-based via URLSearchParams for testing"),
]

ENTRIES = [
    # ── Project / deploy ──
    ("proj-identity", "fact",
     "Identidad del proyecto",
     "Slideshow HTML institucional de Laborteknic (diagnóstico in vitro) publicado en GitHub Pages. "
     "Sin build: editar index.html + assets/img y pushear a main.",
     ["project", "pages"]),
    ("proj-deploy-main", "runbook",
     "Deploy a GitHub Pages",
     "Pages está configurado en la rama main (path /). Commit y git push origin HEAD:main. "
     "Si la rama local se llama master, igual hay que empujar a main. Tras el push esperar rebuild (~30s).",
     ["deploy", "github"]),
    ("pitfall-master-vs-main", "pitfall",
     "master vs main en Pages",
     "Empujar solo a master deja Pages sirviendo HTML viejo. Siempre publicar en main. "
     "Verificar conteo de slides: curl live | grep -c '<section class=\"slide\"'.",
     ["deploy", "pitfall"]),
    ("pitfall-brand-mark", "pitfall",
     "Logo fijo no debe superponerse a títulos",
     "Se quitó el .brand-mark fixed top-left que tapaba los títulos en todas las diapos. "
     "No reintroducir un logo flotante global sin padding claro arriba.",
     ["ui", "pitfall"]),
    ("decision-light-bg", "decision",
     "Fondo claro unificado",
     "Todas las diapos usan theme-paper (claro). Se eliminaron theme-navy/theme-blue/theme-white "
     "como fondos activos. Textos y navegación adaptados a contraste sobre fondo claro.",
     ["design", "theme"]),
    ("decision-assets-local", "decision",
     "Assets self-hosted",
     "Imágenes y logos se descargan del Drive y se sirven desde assets/img (no hotlink a Google Drive). "
     "Optimizar con sips -Z antes de commitear.",
     ["assets", "drive"]),

    # ── Slide structure ──
    ("slides-order", "slide",
     "Orden de diapos (≈20)",
     "0 Portada · 1 Quiénes somos · 2 Instalaciones · 3 Eventos · 4 Austral Farma · 5 BioSystems empresa · "
     "6 Química Clínica (título) · 7–11 Autoanalizadores BTS/A15/A25/BA200/BA400 · 12 Reactivos · "
     "13 Ensayos diferenciales · 14 Autoinmunidad · 15 Prevecal · 16 Snibe · 17 Techlab · 18 Abbott · 19 Cierre.",
     ["slides", "structure"]),
    ("slide-cover", "slide",
     "Portada",
     "Logo Laborteknic + título 'Soluciones integrales para laboratorios de diagnóstico' + pie laborteknic.com. "
     "Sin eyebrow 'diagnóstico in vitro', sin lead largo, sin pills de tagline.",
     ["slides", "cover"]),
    ("slide-quienes", "slide",
     "Quiénes somos",
     "Distribuidor exclusivo BioSystems + Techlab (logos). Distribuidor oficial Snibe + Abbott (logos). "
     "Viñeta soporte técnico/bioquímico pre y posventa. Foto edificio + logo ANMAT overlay al pie de calle.",
     ["slides", "institutional"]),
    ("slide-instalaciones", "slide",
     "Nuestras instalaciones",
     "Grid de 6 áreas: administración, ADV y aplicaciones, expedición, logística, servicio técnico, showroom.",
     ["slides", "institutional"]),
    ("slide-eventos", "slide",
     "En eventos y exposiciones",
     "Texto: Congresos, Ferias y Jornadas con mayúscula. Fotos sin epígrafes (solo imágenes).",
     ["slides", "institutional"]),
    ("slide-austral", "slide",
     "Nuestro socio comercial — Austral Farma",
     "Córdoba: silueta provincia + texto + pills de áreas de suministro. Foto edificio + tira oficinas + "
     "isologo circular australfarma-isologo.png a la derecha de la tira.",
     ["slides", "austral"]),

    # ── BioSystems Química Clínica ──
    ("slide-qc-divider", "slide",
     "Diapo título Química Clínica",
     "Section-divider: eyebrow BioSystems, título Química Clínica (color ink, no blanco), logo BioSystems a la derecha. "
     "Lead sobre autoanalizadores y reactivos.",
     ["slides", "biosystems"]),
    ("slide-autoanalizadores-pattern", "decision",
     "Patrón diapo Autoanalizadores",
     "equip-topbar: eyebrow 'Química Clínica · Autoanalizadores', título Autoanalizadores, logo BioSystems. "
     "Imagen principal + detalle inset. Modelo + tag Semiautomático/Automático. Bullets + specs del Word de equipamiento.",
     ["slides", "biosystems", "pattern"]),
    ("product-bts", "product",
     "BTS — semiautomático",
     "LED 340–670 nm, reactivos BioSystems, software intuitivo, LIS/móviles, bajo mantenimiento sin recambio de lámpara.",
     ["biosystems", "analyzer"]),
    ("product-a15", "product",
     "A15 — automático 150 test/hora",
     "150 test/hora (cartel overlay). Reactivos refrigerados/no refrigerados, config abierta, LIS. Hasta 72 muestras, 30 reactivos.",
     ["biosystems", "analyzer"]),
    ("product-a25", "product",
     "A25 — automático 240 test/hora",
     "240 test/hora (cartel overlay). Acceso aleatorio/continuo, predilución/posdilución, 52 reactivos, 72 muestras.",
     ["biosystems", "analyzer"]),
    ("product-ba200", "product",
     "BA 200 — automático",
     "200 ciclos/h (300 con ISE). 88 posiciones, SMART LED, ISE Na/K/Cl/Li opcional. Suero, plasma, orina.",
     ["biosystems", "analyzer"]),
    ("product-ba400", "product",
     "BA 400 — automático",
     "400 t/h (560 con ISE). Hemólisis sangre entera, rotor segmentado, 88 reactivos 6–11°C, LIS ASTM/HL7.",
     ["biosystems", "analyzer"]),
    ("slide-reactivos", "slide",
     "Reactivos — paneles con iconos",
     "Mismo topbar: 'Química Clínica · Reactivos' + Reactivos + logo BioSystems. Collage de 6 fotos reactivos. "
     "14 paneles con iconitos naranjas del Word (assets/img/panels/). Inflamatorio: icono recreado (faltaba en el Word).",
     ["slides", "biosystems", "reactivos"]),
    ("slide-ensayos", "slide",
     "Ensayos diferenciales (8)",
     "Diapo aparte con los 8: NEFA, ADA, Oxalato, Citrato, β-Hidroxibutirato, α1-Glicoproteína ácida, G6PD, Cobre. Sin etc.",
     ["slides", "biosystems", "reactivos"]),
    ("source-docs-qc", "fact",
     "Fuentes Drive — Química Clínica",
     "Carpeta 02.1: Línea Biosystems descripción equipamiento; Biosystems descripción reactivos (iconos DrawingML); "
     "Ensayos diferenciales.docx; 6 JPG reactivos biosystems*.",
     ["drive", "source"]),

    # ── Other brands ──
    ("brand-snibe", "brand",
     "Snibe",
     "Marca de inmunoensayo / Maglumi etc. Diapo propia tras Prevecal/Autoinmunidad en el deck.",
     ["snibe", "brand"]),
    ("brand-techlab", "brand",
     "Techlab",
     "Kits rápidos entéricos (Shiga Toxin Quik Chek, C. Diff Quik Chek Complete). Distribuidor exclusivo Laborteknic.",
     ["techlab", "brand"]),
    ("brand-abbott", "brand",
     "Abbott Rapid Diagnostics — Toxicología",
     "Distribuidor oficial división toxicología: SoToxa, SureStep, ABON. Detección drogas orina/saliva/fluido oral.",
     ["abbott", "brand"]),
]


def main() -> None:
    if DB.exists():
        DB.unlink()
    con = duckdb.connect(str(DB))
    con.execute(SCHEMA.read_text())

    con.execute(
        """
        INSERT INTO project VALUES (?, ?, ?, ?, ?, ?, ?, current_timestamp)
        """,
        [
            PROJECT["id"],
            PROJECT["display_name"],
            PROJECT["repo_path"],
            PROJECT["repo_github"],
            PROJECT["live_url"],
            PROJECT["deploy_branch"],
            PROJECT["stack"],
        ],
    )

    con.executemany(
        "INSERT INTO constants VALUES (?, ?, ?)",
        CONSTANTS,
    )
    con.executemany(
        "INSERT INTO entries VALUES (?, ?, ?, ?, ?)",
        [(e[0], e[1], e[2], e[3], e[4]) for e in ENTRIES],
    )

    n = con.execute("SELECT count(*) FROM entries").fetchone()[0]
    con.close()
    print(f"Seeded {DB.name}: {n} entries")


if __name__ == "__main__":
    main()
