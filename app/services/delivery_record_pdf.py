import base64
import json
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 34
BLUE = colors.HexColor("#30516f")
LIGHT_BLUE = colors.HexColor("#eaf0f5")
TEXT = colors.HexColor("#34495e")


def _safe(value) -> str:
    return str(value or "-")


def _field(pdf, x, y, label: str, value, width: float) -> None:
    pdf.setFont("Helvetica-Bold", 7)
    pdf.setFillColor(BLUE)
    pdf.drawString(x, y, label)
    pdf.setFillColor(TEXT)
    pdf.setFont("Helvetica", 8)
    clipped = _safe(value)
    while stringWidth(clipped, "Helvetica", 8) > width and len(clipped) > 3:
        clipped = clipped[:-4] + "..."
    pdf.drawString(x, y - 12, clipped)
    pdf.setStrokeColor(colors.HexColor("#cbd5e1"))
    pdf.line(x, y - 15, x + width, y - 15)


def _section(pdf, y: float, number: int, title: str) -> float:
    pdf.setFillColor(LIGHT_BLUE)
    pdf.rect(MARGIN, y - 17, PAGE_WIDTH - MARGIN * 2, 18, fill=1, stroke=0)
    pdf.setFillColor(BLUE)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(MARGIN + 8, y - 11, f"{number}.  {title.upper()}")
    return y - 30


def build_delivery_record_pdf(record, integrity_hash: str) -> BytesIO:
    """Genera la versión imprimible e inmutable de una acta firmada."""
    stream = BytesIO()
    pdf = canvas.Canvas(stream, pagesize=A4, pageCompression=1)
    pdf.setTitle(f"Acta de entrega {record.reference}")
    y = PAGE_HEIGHT - 38

    pdf.setFillColor(colors.HexColor("#049DD9"))
    pdf.roundRect(MARGIN, y - 28, 100, 25, 3, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(MARGIN + 50, y - 20, "GEIMSER")
    pdf.setFillColor(TEXT)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(MARGIN + 116, y - 13, "ACTA DE ENTREGA Y RECEPCIÓN")
    pdf.setFont("Helvetica", 8)
    pdf.drawString(MARGIN + 116, y - 25, "DE EQUIPAMIENTO COMPUTACIONAL")
    pdf.drawRightString(PAGE_WIDTH - MARGIN, y - 13, f"Fecha: {record.delivery_date.strftime('%d-%m-%Y')}")
    pdf.drawRightString(PAGE_WIDTH - MARGIN, y - 25, f"Acta: {record.reference}")
    y -= 49

    y = _section(pdf, y, 1, "Datos del funcionario responsable")
    half = (PAGE_WIDTH - MARGIN * 2 - 14) / 2
    _field(pdf, MARGIN + 8, y, "Nombre completo", record.recipient_name, half)
    _field(pdf, MARGIN + 16 + half, y, "RUN", record.recipient_run, half)
    y -= 31
    _field(pdf, MARGIN + 8, y, "Cargo / función", record.recipient_role, half)
    _field(pdf, MARGIN + 16 + half, y, "Calidad jurídica", record.employment_type, half)
    y -= 31
    _field(pdf, MARGIN + 8, y, "Unidad / departamento", record.recipient_unit, half)
    _field(pdf, MARGIN + 16 + half, y, "Sede", record.site, half)
    y -= 27

    y = _section(pdf, y, 2, "Identificación del equipo entregado")
    _field(pdf, MARGIN + 8, y, "Tipo de equipo", record.equipment_type, half)
    _field(pdf, MARGIN + 16 + half, y, "Marca y modelo", record.equipment_brand_model, half)
    y -= 31
    _field(pdf, MARGIN + 8, y, "N° de serie", record.equipment_serial, half)
    _field(pdf, MARGIN + 16 + half, y, "Nombre del equipo", record.equipment_hostname, half)
    y -= 31
    _field(pdf, MARGIN + 8, y, "Dirección MAC", record.mac_address, half)
    _field(pdf, MARGIN + 16 + half, y, "N° de rótulo", record.label_number, half)
    y -= 31
    _field(pdf, MARGIN + 8, y, "N° de serie pantalla adicional", record.monitor_serial, half)
    _field(pdf, MARGIN + 16 + half, y, "N° de serie dock", record.dock_serial, half)
    y -= 31
    accessories = ", ".join(json.loads(record.accessories_json or "[]")) or "Sin accesorios registrados"
    migration = ", ".join(json.loads(record.migration_json or "[]")) or "No aplica"
    _field(pdf, MARGIN + 8, y, "Adicionales", accessories, half)
    _field(pdf, MARGIN + 16 + half, y, "Estado al entregar", record.delivery_condition, half)
    y -= 31
    _field(pdf, MARGIN + 8, y, "Migración de data", migration, PAGE_WIDTH - MARGIN * 2 - 16)
    y -= 27

    y = _section(pdf, y, 3, "Identificación del equipo retirado")
    returned = json.loads(record.returned_equipment_json or "{}")
    if returned.get("applies"):
        _field(pdf, MARGIN + 8, y, "Tipo de equipo", returned.get("equipment_type"), half)
        _field(pdf, MARGIN + 16 + half, y, "Marca y modelo", returned.get("brand_model"), half)
        y -= 31
        _field(pdf, MARGIN + 8, y, "N° de serie", returned.get("serial"), half)
        _field(pdf, MARGIN + 16 + half, y, "Motivo de retiro", returned.get("reason"), half)
        y -= 31
        _field(pdf, MARGIN + 8, y, "Estado operacional", returned.get("operational_status"), PAGE_WIDTH - MARGIN * 2 - 16)
    else:
        _field(pdf, MARGIN + 8, y, "Equipo retirado", "No aplica (primera entrega)", PAGE_WIDTH - MARGIN * 2 - 16)
    y -= 31
    _field(pdf, MARGIN + 8, y, "Observaciones", record.observations, PAGE_WIDTH - MARGIN * 2 - 16)
    y -= 27

    y = _section(pdf, y, 4, "Declaración de responsabilidad")
    statement = (
        "La persona receptora asume la custodia y responsabilidad del equipamiento descrito, "
        "destinándolo exclusivamente a labores institucionales. Se compromete a proteger la información, "
        "no instalar software no autorizado y reportar de inmediato cualquier pérdida, daño o extravío."
    )
    pdf.setFillColor(TEXT)
    pdf.setFont("Helvetica", 7.2)
    words, line = statement.split(), ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if stringWidth(candidate, "Helvetica", 7.2) > PAGE_WIDTH - MARGIN * 2 - 16:
            pdf.drawString(MARGIN + 8, y, line); y -= 10; line = word
        else:
            line = candidate
    if line: pdf.drawString(MARGIN + 8, y, line)
    y -= 21

    y = _section(pdf, y, 5, "Firmas de conformidad")
    columns = [MARGIN + 15, PAGE_WIDTH / 2 - 64, PAGE_WIDTH - MARGIN - 143]
    titles = ["ENTREGA CONFORME", "RECEPCIÓN CONFORME", "TÉCNICO INSTALADOR"]
    for x, title in zip(columns, titles):
        pdf.setFillColor(BLUE); pdf.setFont("Helvetica-Bold", 7.5); pdf.drawCentredString(x + 57, y, title)
        pdf.setStrokeColor(colors.HexColor("#64748b")); pdf.line(x, y - 54, x + 114, y - 54)
    pdf.setFillColor(TEXT); pdf.setFont("Helvetica", 7)
    pdf.drawCentredString(columns[0] + 57, y - 66, record.created_by.full_name if record.created_by else "Encargado GEIMSER")
    pdf.drawCentredString(columns[1] + 57, y - 66, record.recipient_signer_name or record.recipient_name)
    pdf.drawCentredString(columns[2] + 57, y - 66, "Técnico responsable")
    if record.recipient_signature_data:
        try:
            raw = base64.b64decode(record.recipient_signature_data.split(",", 1)[1])
            pdf.drawImage(ImageReader(BytesIO(raw)), columns[1] + 15, y - 49, width=84, height=34, preserveAspectRatio=True, mask="auto")
        except Exception:
            pass

    pdf.setStrokeColor(colors.HexColor("#cbd5e1")); pdf.line(MARGIN, 30, PAGE_WIDTH - MARGIN, 30)
    pdf.setFillColor(colors.HexColor("#64748b")); pdf.setFont("Helvetica", 6.5)
    pdf.drawString(MARGIN, 19, f"Documento firmado digitalmente el {record.recipient_signed_at.strftime('%d-%m-%Y %H:%M UTC')}.")
    pdf.drawRightString(PAGE_WIDTH - MARGIN, 19, f"Integridad SHA-256: {integrity_hash}")
    pdf.save()
    stream.seek(0)
    return stream
