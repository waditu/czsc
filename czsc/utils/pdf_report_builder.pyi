import pandas as pd
from _typeshed import Incomplete
from reportlab.lib.enums import TA_RIGHT as TA_RIGHT
from reportlab.lib.units import mm as mm
from reportlab.platypus import KeepTogether as KeepTogether
from typing import Any

COLOR_PRIMARY: Incomplete
COLOR_SUCCESS: Incomplete
COLOR_DANGER: Incomplete
COLOR_WARNING: Incomplete
COLOR_SECONDARY: Incomplete
COLOR_LIGHT: Incomplete
COLOR_DARK: Incomplete
COLOR_BORDER: Incomplete
COLOR_SUCCESS_BG: Incomplete
COLOR_DANGER_BG: Incomplete
COLOR_PRIMARY_BG: Incomplete
PAGE_SIZE: Incomplete
PAGE_WIDTH: Incomplete
PAGE_HEIGHT: Incomplete
MARGIN_TOP: Incomplete
MARGIN_BOTTOM: Incomplete
MARGIN_LEFT: Incomplete
MARGIN_RIGHT: Incomplete
CONTENT_WIDTH: Incomplete
CONTENT_HEIGHT: Incomplete
CM_TO_PX: Incomplete
CARD_SPACING: int
FONT_NAME: str
FONT_NAME_BOLD: str

class PdfReportBuilder:
    title: Incomplete
    author: Incomplete
    created_at: Incomplete
    def __init__(self, title: str = 'PDF 报告', author: str = 'CZSC') -> None: ...
    def add_header(self, params: dict[str, str], subtitle: str = None) -> PdfReportBuilder: ...
    def add_toc(self, title: str = '目 录') -> PdfReportBuilder: ...
    def insert_toc_after_header(self, title: str = '目 录', add_page_break: bool = True) -> PdfReportBuilder: ...
    def add_page_break(self) -> PdfReportBuilder: ...
    def add_metrics(self, metrics: list[dict[str, Any]], title: str = '核心绩效指标') -> PdfReportBuilder: ...
    def add_chart(self, fig_or_image, title: str = '图表', height: float = None, fit_page: bool = False, aspect_ratio: float = 0.55) -> PdfReportBuilder: ...
    def add_table(self, df: pd.DataFrame, title: str = '数据表', max_rows: int = None) -> PdfReportBuilder: ...
    def add_section(self, title: str, content: str) -> PdfReportBuilder: ...
    def add_footer(self, text: str = None) -> PdfReportBuilder: ...
    def render(self) -> bytes: ...
    def save(self, file_path: str) -> str: ...
