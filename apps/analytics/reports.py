"""
Генерация отчетов в разных форматах (PDF, Excel).
"""
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
import pandas as pd


def generate_pdf_report(data, report_type='orders'):
    """
    Генерирует PDF отчет.
    """
    buffer = BytesIO()
    
    # Создаем документ
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    # Заголовок
    title = Paragraph(f"Отчет: {report_type}", styles['Title'])
    story.append(title)
    
    # Данные
    if isinstance(data, list) and len(data) > 0:
        # Создаем таблицу
        table_data = []
        
        # Заголовки таблицы
        if data:
            headers = list(data[0].keys())
            table_data.append(headers)
        
        # Данные
        for item in data:
            table_data.append([str(item.get(key, '')) for key in headers])
        
        # Создаем таблицу
        table = Table(table_data)
        
        # Стиль таблицы
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
    
    # Строим PDF
    doc.build(story)
    
    buffer.seek(0)
    return buffer


def generate_excel_report(data, report_type='orders'):
    """
    Генерирует Excel отчет.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = report_type
    
    if isinstance(data, list) and len(data) > 0:
        # Заголовки
        headers = list(data[0].keys())
        ws.append(headers)
        
        # Данные
        for item in data:
            row = [item.get(key, '') for key in headers]
            ws.append(row)
        
        # Форматирование заголовков
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center')
    
    # Сохраняем в буфер
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    return buffer