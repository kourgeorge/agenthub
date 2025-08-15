"""
PDF Invoice Generator Service

This service handles the generation of PDF invoices for users based on their billing data.
"""

import io
import json
from datetime import datetime
from typing import Dict, Any, List
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.pdfgen import canvas
import logging

logger = logging.getLogger(__name__)


class PDFInvoiceGenerator:
    """Generates professional PDF invoices with enhanced branding"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
        # Brand colors
        self.primary_color = colors.HexColor('#1e40af')  # Blue-800
        self.secondary_color = colors.HexColor('#3b82f6')  # Blue-500
        self.accent_color = colors.HexColor('#f59e0b')  # Amber-500
        self.text_color = colors.HexColor('#1f2937')  # Gray-800
        self.light_gray = colors.HexColor('#f3f4f6')  # Gray-100
        self.border_color = colors.HexColor('#d1d5db')  # Gray-300
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles for the invoice"""
        # Main title style
        self.styles.add(ParagraphStyle(
            name='InvoiceTitle',
            parent=self.styles['Heading1'],
            fontSize=32,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1e40af'),
            fontName='Helvetica-Bold'
        ))
        
        # Company name style
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            parent=self.styles['Normal'],
            fontSize=18,
            spaceAfter=5,
            alignment=TA_LEFT,
            textColor=colors.HexColor('#1e40af'),
            fontName='Helvetica-Bold'
        ))
        
        # Company tagline style
        self.styles.add(ParagraphStyle(
            name='CompanyTagline',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=20,
            alignment=TA_LEFT,
            textColor=colors.HexColor('#6b7280'),
            fontName='Helvetica'
        ))
        
        # Invoice details style
        self.styles.add(ParagraphStyle(
            name='InvoiceDetails',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=5,
            alignment=TA_LEFT,
            textColor=colors.HexColor('#374151'),
            fontName='Helvetica'
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=15,
            textColor=colors.HexColor('#1e40af'),
            fontName='Helvetica-Bold',
            spaceBefore=20
        ))
        
        # Invoice number style
        self.styles.add(ParagraphStyle(
            name='InvoiceNumber',
            parent=self.styles['Normal'],
            fontSize=14,
            spaceAfter=10,
            alignment=TA_RIGHT,
            textColor=colors.HexColor('#1e40af'),
            fontName='Helvetica-Bold'
        ))
        
        # Table header style
        self.styles.add(ParagraphStyle(
            name='TableHeader',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=5,
            textColor=colors.white,
            fontName='Helvetica-Bold'
        ))
        
        # Footer style
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=9,
            spaceAfter=5,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#6b7280'),
            fontName='Helvetica'
        ))
    
    def generate_invoice_pdf(self, invoice_data: Dict[str, Any], user_data: Dict[str, Any]) -> bytes:
        """
        Generate a PDF invoice from invoice and user data
        
        Args:
            invoice_data: Invoice information including billing data
            user_data: User information (name, email, etc.)
            
        Returns:
            PDF file as bytes
        """
        try:
            # Create PDF document
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, 
                                  topMargin=72, bottomMargin=18)
            
            # Build PDF content
            story = []
            
            # Add header with logo and branding
            story.extend(self._create_header(invoice_data, user_data))
            
            # Add invoice details section
            story.extend(self._create_invoice_details(invoice_data))
            
            # Add billing summary
            story.extend(self._create_billing_summary(invoice_data))
            
            # Add detailed breakdown
            story.extend(self._create_detailed_breakdown(invoice_data))
            
            # Add payment information
            story.extend(self._create_payment_info(invoice_data))
            
            # Add footer
            story.extend(self._create_footer())
            
            # Build PDF
            doc.build(story)
            
            # Get PDF bytes
            pdf_bytes = buffer.getvalue()
            buffer.close()
            
            logger.info(f"Successfully generated PDF invoice for invoice {invoice_data.get('invoice_number', 'unknown')}")
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"Failed to generate PDF invoice: {str(e)}")
            raise
    
    def _create_header(self, invoice_data: Dict[str, Any], user_data: Dict[str, Any]) -> List:
        """Create the invoice header section with enhanced branding"""
        elements = []
        
        # Company branding section
        company_branding = [
            ["", ""],  # Spacer row
            ["", ""],  # Spacer row
        ]
        
        # Company info (left side)
        company_info = [
            ["", ""],
            ["", ""],
            ["", ""],
            ["", ""],
            ["", ""],
            ["", ""],
        ]
        
        # Company details
        company_info[0][0] = Paragraph("AGENTHUB", self.styles['CompanyName'])
        company_info[1][0] = Paragraph("AI Agent Platform", self.styles['CompanyTagline'])
        company_info[2][0] = Paragraph("123 AI Innovation Drive", self.styles['InvoiceDetails'])
        company_info[3][0] = Paragraph("San Francisco, CA 94105", self.styles['InvoiceDetails'])
        company_info[4][0] = Paragraph("support@agenthub.com", self.styles['InvoiceDetails'])
        company_info[5][0] = Paragraph("https://agenthub.com", self.styles['InvoiceDetails'])
        
        # Customer info (right side)
        company_info[0][1] = Paragraph("BILL TO:", self.styles['SectionHeader'])
        company_info[1][1] = Paragraph(f"{user_data.get('username', 'User').title()}", self.styles['InvoiceDetails'])
        company_info[2][1] = Paragraph(f"{user_data.get('email', '')}", self.styles['InvoiceDetails'])
        company_info[3][1] = Paragraph("", self.styles['InvoiceDetails'])  # Spacer
        company_info[4][1] = Paragraph(f"Invoice Date: {datetime.now().strftime('%B %d, %Y')}", self.styles['InvoiceDetails'])
        company_info[5][1] = Paragraph(f"Invoice #: {invoice_data.get('invoice_number', 'N/A')}", self.styles['InvoiceDetails'])
        
        # Create company info table
        company_table = Table(company_info, colWidths=[3.5*inch, 3.5*inch])
        company_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        elements.append(company_table)
        elements.append(Spacer(1, 30))
        
        # Main title with decorative line
        title = Paragraph("INVOICE", self.styles['InvoiceTitle'])
        elements.append(title)
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _create_invoice_details(self, invoice_data: Dict[str, Any]) -> List:
        """Create invoice details section with improved styling"""
        elements = []
        
        # Section header
        section_header = Paragraph("Invoice Information", self.styles['SectionHeader'])
        elements.append(section_header)
        
        # Invoice information table
        billing_data = invoice_data.get('billing_data', {})
        billing_period = billing_data.get('billing_period', {})
        
        # Format dates nicely
        start_date = billing_period.get('start', '')
        end_date = billing_period.get('end', '')
        if start_date and end_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                billing_period_str = f"{start_dt.strftime('%B %d, %Y')} - {end_dt.strftime('%B %d, %Y')}"
            except:
                billing_period_str = f"{start_date} to {end_date}"
        else:
            billing_period_str = "N/A"
        
        invoice_info = [
            ["Invoice Number:", invoice_data.get('invoice_number', 'N/A')],
            ["Invoice Date:", datetime.now().strftime('%B %d, %Y')],
            ["Due Date:", invoice_data.get('due_date', 'N/A')],
            ["Billing Period:", billing_period_str],
            ["Status:", invoice_data.get('status', 'N/A').upper()],
            ["Currency:", "USD"],
        ]
        
        invoice_table = Table(invoice_info, colWidths=[2*inch, 4*inch])
        invoice_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, self.border_color),
            ('BACKGROUND', (0, 0), (0, -1), self.light_gray),
            ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        
        elements.append(invoice_table)
        elements.append(Spacer(1, 25))
        
        return elements
    
    def _create_billing_summary(self, invoice_data: Dict[str, Any]) -> List:
        """Create billing summary section with enhanced styling"""
        elements = []
        
        # Section header
        section_header = Paragraph("Billing Summary", self.styles['SectionHeader'])
        elements.append(section_header)
        
        # Summary table
        billing_data = invoice_data.get('billing_data', {})
        total_charges = billing_data.get('total_charges', 0)
        
        summary_data = [
            ["Description", "Quantity", "Unit Rate", "Amount"],
            ["AI Agent Executions", billing_data.get('execution_count', 0), "$0.01 per execution", f"${total_charges:.2f}"],
            ["", "", "", ""],
            ["", "", "Total Amount:", f"${total_charges:.2f}"],
        ]
        
        summary_table = Table(summary_data, colWidths=[2.5*inch, 1*inch, 1.5*inch, 1*inch])
        summary_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, 0), 1, self.primary_color),
            ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 1), (-1, -1), 1, self.border_color),
            ('LINEBELOW', (0, 2), (-1, 2), 2, self.primary_color),
            ('LINEBELOW', (0, 3), (-1, 3), 2, self.primary_color),
            ('FONTNAME', (0, 3), (-1, 3), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 3), (-1, 3), 12),
            ('BACKGROUND', (0, 3), (-1, 3), self.light_gray),
            ('TEXTCOLOR', (0, 3), (-1, 3), self.primary_color),
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 25))
        
        return elements
    
    def _create_detailed_breakdown(self, invoice_data: Dict[str, Any]) -> List:
        """Create detailed breakdown section with improved table styling"""
        elements = []
        
        # Section header
        section_header = Paragraph("Detailed Execution Breakdown", self.styles['SectionHeader'])
        elements.append(section_header)
        
        billing_data = invoice_data.get('billing_data', {})
        executions = billing_data.get('executions', [])
        
        if executions:
            # Create detailed execution table
            detailed_data = [["Execution ID", "Agent Name", "Cost", "Date", "Resource Usage"]]
            
            for execution in executions:
                # Format date
                try:
                    exec_date = datetime.fromisoformat(execution.get('created_at', '')).strftime('%m/%d/%Y')
                except:
                    exec_date = execution.get('created_at', 'N/A')
                
                # Create resource summary
                resource_summary = ", ".join([
                    f"{r['resource_type']}: ${r['cost']:.4f}"
                    for r in execution.get('resource_usage', [])
                ])
                
                detailed_data.append([
                    str(execution.get('execution_id', 'N/A')),
                    execution.get('agent_name', 'Unknown'),
                    f"${execution.get('cost', 0):.4f}",
                    exec_date,
                    resource_summary[:60] + "..." if len(resource_summary) > 60 else resource_summary
                ])
            
            detailed_table = Table(detailed_data, colWidths=[1*inch, 1.5*inch, 0.8*inch, 1*inch, 2.7*inch])
            detailed_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, 0), 1, self.primary_color),
                ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 1), (-1, -1), 1, self.border_color),
                ('ROWBACKGROUNDS', (1, 1), (-1, -1), [colors.white, self.light_gray]),
            ]))
            
            elements.append(detailed_table)
        else:
            # No executions message
            no_data = Paragraph(
                "No detailed execution data available for this billing period.", 
                self.styles['InvoiceDetails']
            )
            elements.append(no_data)
        
        elements.append(Spacer(1, 25))
        
        return elements
    
    def _create_payment_info(self, invoice_data: Dict[str, Any]) -> List:
        """Create payment information section"""
        elements = []
        
        # Section header
        section_header = Paragraph("Payment Information", self.styles['SectionHeader'])
        elements.append(section_header)
        
        # Payment details
        payment_info = [
            ["Payment Method:", "Credit Card / Stripe"],
            ["Payment Status:", invoice_data.get('status', 'Pending').upper()],
            ["Due Date:", invoice_data.get('due_date', '30 days from invoice date')],
            ["Late Fee:", "2.5% per month on overdue amounts"],
        ]
        
        payment_table = Table(payment_info, colWidths=[2*inch, 4*inch])
        payment_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, self.border_color),
            ('BACKGROUND', (0, 0), (0, -1), self.light_gray),
        ]))
        
        elements.append(payment_table)
        elements.append(Spacer(1, 25))
        
        return elements
    
    def _create_footer(self) -> List:
        """Create enhanced invoice footer section"""
        elements = []
        
        # Add a decorative line
        elements.append(Spacer(1, 20))
        
        # Footer information with simple ReportLab-compatible formatting
        footer_text = """
        <b>Payment Terms:</b><br/>
        Payment is due within 30 days of invoice date. Late payments may incur additional fees.<br/>
        <br/>
        <b>Contact Information:</b><br/>
        Email: support@agenthub.com<br/>
        Website: https://agenthub.com<br/>
        Support: Available 24/7<br/>
        <br/>
        <b>Thank you for choosing AgentHub!</b><br/>
        Empowering your business with AI agents
        """
        
        footer = Paragraph(footer_text, self.styles['Footer'])
        elements.append(footer)
        
        return elements
