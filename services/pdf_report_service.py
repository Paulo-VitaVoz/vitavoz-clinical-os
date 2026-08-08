"""Serviço de aplicação para compilação e exportação de Dossiês Clínicos em PDF."""

from datetime import datetime
import hashlib
import io
import os
from typing import List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.domain.entities.care_event import CareEvent
from src.domain.entities.evolution import Evolution
from src.domain.entities.patient import Patient
from src.domain.entities.protocol import Protocol


class PDFReportService:
    """Caso de uso de aplicação para geração de documentos PDF auditáveis."""

    def generate_patient_dossier(
        self,
        patient: Patient,
        evolutions: List[Evolution],
        care_events: List[CareEvent],
        protocol: Optional[Protocol] = None,
        doctor_name: str = "Dr. Davi",
        clinic_name: str = "Clínica Prime • Odontologia Especializada",
        logo_path: Optional[str] = None,
    ) -> io.BytesIO:
        """
        Compila o histórico pós-operatório completo do paciente em um documento PDF A4 em buffer de memória.

        Suporta opcionalmente um logotipo de clínica customizado no cabeçalho.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0F172A"),
            fontName="Helvetica-Bold",
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#64748B"),
            fontName="Helvetica",
        )
        section_heading = ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#0F172A"),
            fontName="Helvetica-Bold",
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "BodyDark",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#334155"),
            fontName="Helvetica",
        )
        body_bold = ParagraphStyle(
            "BodyDarkBold",
            parent=body_style,
            fontName="Helvetica-Bold",
        )
        table_cell_style = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#1E293B"),
            fontName="Helvetica",
        )
        table_cell_bold = ParagraphStyle(
            "TableCellBold",
            parent=table_cell_style,
            fontName="Helvetica-Bold",
        )

        story = []

        # 1. Cabeçalho Institucional
        if logo_path and os.path.exists(logo_path):
            img = Image(logo_path, width=120, height=40)
            story.append(img)
            story.append(Spacer(1, 6))

        header_text = f"<b>{clinic_name}</b><br/><font size=8 color='#64748B'>VitaVoz Clinical OS — Sistema de Monitoramento Preditivo</font>"
        story.append(Paragraph(header_text, subtitle_style))
        story.append(Spacer(1, 8))
        story.append(Paragraph("DOSSIÊ CLÍNICO DE ACOMPANHAMENTO PÓS-OPERATÓRIO", title_style))
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0F172A"), spaceAfter=12))

        # 2. Dados do Paciente e do Procedimento
        proto_nome = protocol.nome_procedimento if protocol else patient.protocolo
        patient_info_data = [
            [
                Paragraph(f"<b>Paciente:</b> {patient.nome}", body_style),
                Paragraph(f"<b>Idade:</b> {patient.idade} anos", body_style),
                Paragraph(f"<b>Cirurgia:</b> {patient.procedimento}", body_style),
            ],
            [
                Paragraph(f"<b>Data Cirurgia:</b> {patient.data_cirurgia}", body_style),
                Paragraph(f"<b>Retorno Previsto:</b> {patient.data_retorno}", body_style),
                Paragraph(f"<b>Protocolo:</b> {proto_nome}", body_style),
            ],
            [
                Paragraph(f"<b>Cirurgião Responsável:</b> {doctor_name}", body_style),
                Paragraph(f"<b>Anamnese/Alertas:</b> {patient.alertas_clinicos}", body_style),
                Paragraph("", body_style),
            ],
        ]
        info_table = Table(patient_info_data, colWidths=[200, 150, 172])
        info_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#F1F5F9")),
            ])
        )
        story.append(info_table)
        story.append(Spacer(1, 14))

        # 3. Métrica Atual e Alerta Explicável
        ultima_ev = evolutions[0] if evolutions else None
        status_txt = ultima_ev.status_alerta if ultima_ev else "🟢 Normal"
        score_val = ultima_ev.score if ultima_ev else 100
        motivo_txt = ultima_ev.motivo if ultima_ev else "Sem registros de alertas."

        story.append(Paragraph("SITUAÇÃO CLÍNICA ATUAL", section_heading))
        status_box_data = [
            [
                Paragraph(f"<b>VitaScore™:</b> {score_val}/100", body_bold),
                Paragraph(f"<b>Status Clínico:</b> {status_txt}", body_bold),
            ],
            [
                Paragraph(f"<b>Parecer Técnico / Motivo:</b> {motivo_txt}", body_style),
                Paragraph("", body_style),
            ],
        ]
        status_table = Table(status_box_data, colWidths=[200, 322])
        bg_color = colors.HexColor("#FEF2F2") if "🟡" in status_txt or "🔴" in status_txt else colors.HexColor("#F0FDF4")
        border_color = colors.HexColor("#FCA5A5") if "🟡" in status_txt or "🔴" in status_txt else colors.HexColor("#86EFAC")

        status_table.setStyle(
            TableStyle([
                ("SPAN", (0, 1), (1, 1)),
                ("BACKGROUND", (0, 0), (-1, -1), bg_color),
                ("BOX", (0, 0), (-1, -1), 1, border_color),
                ("PADDING", (0, 0), (-1, -1), 8),
            ])
        )
        story.append(status_table)
        story.append(Spacer(1, 14))

        # 4. Tabela de Care Timeline (Fatos Clínicos Auditáveis)
        story.append(Paragraph("TRILHA DE AUDITORIA CLÍNICA (CARE TIMELINE)", section_heading))
        timeline_headers = [
            Paragraph("Data/Hora", table_cell_bold),
            Paragraph("Evento", table_cell_bold),
            Paragraph("Descrição", table_cell_bold),
            Paragraph("Autor", table_cell_bold),
        ]
        timeline_rows = [timeline_headers]

        for event in care_events:
            timeline_rows.append([
                Paragraph(event.timestamp, table_cell_style),
                Paragraph(f"<b>{event.title}</b>", table_cell_style),
                Paragraph(event.description, table_cell_style),
                Paragraph(event.author, table_cell_style),
            ])

        timeline_table = Table(timeline_rows, colWidths=[90, 130, 212, 90])
        timeline_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("PADDING", (0, 0), (-1, -1), 5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ])
        )
        for i in range(4):
            timeline_rows[0][i].style.textColor = colors.white

        story.append(timeline_table)
        story.append(Spacer(1, 14))

        # 5. Seção de Conduta Médica Registrada (Closed-Loop Care)
        conduta_texto = ultima_ev.conduta_medico if (ultima_ev and ultima_ev.conduta_medico) else "Nenhuma conduta de intervenção foi requerida até o momento."
        conduta_data = ultima_ev.data_conduta if (ultima_ev and ultima_ev.data_conduta) else "-"

        story.append(Paragraph("CONDUTA E ORIENTAÇÃO MÉDICA REGISTRADA", section_heading))
        conduta_box_data = [
            [
                Paragraph(f"<b>Data da Conduta:</b> {conduta_data} | <b>Cirurgião:</b> {doctor_name}", body_bold),
            ],
            [
                Paragraph(f"<i>\"{conduta_texto}\"</i>", body_style),
            ],
        ]
        conduta_table = Table(conduta_box_data, colWidths=[522])
        conduta_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#BFDBFE")),
                ("PADDING", (0, 0), (-1, -1), 8),
            ])
        )
        story.append(conduta_table)
        story.append(Spacer(1, 18))

        # 6. Rodapé de Auditoria e Hash de Integridade
        timestamp_emissao = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
        raw_hash_seed = f"{patient.nome}_{patient.procedimento}_{timestamp_emissao}"
        hash_autenticidade = hashlib.sha256(raw_hash_seed.encode("utf-8")).hexdigest().upper()[:16]

        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#94A3B8"), spaceAfter=8))
        footer_text = (
            f"<b>Dossiê gerado em:</b> {timestamp_emissao} | "
            f"<b>Código de Autenticidade Documental:</b> {hash_autenticidade}<br/>"
            f"<font size=7 color='#94A3B8'>Este documento é um registro compilado automaticamente pelo VitaVoz Clinical OS. "
            f"A validação técnica do acompanhamento cabe exclusivamente ao cirurgião responsável.</font>"
        )
        story.append(Paragraph(footer_text, subtitle_style))

        doc.build(story)
        buffer.seek(0)
        return buffer
