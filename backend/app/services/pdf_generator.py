"""
PDF Synthetic Data Generator using GPT
Extracts content from sample PDFs and generates similar synthetic PDFs
"""

import os
import io
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
import requests
from datetime import datetime
import PyPDF2
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib import colors
from reportlab.pdfgen import canvas
import warnings
warnings.filterwarnings('ignore')

from app.utils.logger import get_logger

logger = get_logger(__name__)


class PDFExtractor:
    """Extract and analyze content from PDF files"""

    @staticmethod
    def extract_text_from_pdf(pdf_path: str) -> Dict[str, Any]:
        """
        Extract text and metadata from a PDF file

        Returns:
            Dictionary with text, page_count, and metadata
        """
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)

                # Extract metadata
                metadata = {
                    'page_count': len(pdf_reader.pages),
                    'title': '',
                    'author': '',
                    'subject': ''
                }

                # Try to get metadata
                if pdf_reader.metadata:
                    metadata['title'] = pdf_reader.metadata.get('/Title', '')
                    metadata['author'] = pdf_reader.metadata.get('/Author', '')
                    metadata['subject'] = pdf_reader.metadata.get('/Subject', '')

                # Extract text from all pages
                pages_text = []
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        text = page.extract_text()
                        pages_text.append({
                            'page_num': page_num + 1,
                            'text': text.strip(),
                            'word_count': len(text.split())
                        })
                    except Exception as e:
                        logger.error(f"Error extracting page {page_num + 1}: {e}")
                        pages_text.append({
                            'page_num': page_num + 1,
                            'text': '',
                            'word_count': 0
                        })

                # Calculate statistics
                total_text = ' '.join([p['text'] for p in pages_text])

                return {
                    'success': True,
                    'filename': os.path.basename(pdf_path),
                    'metadata': metadata,
                    'pages': pages_text,
                    'total_pages': len(pages_text),
                    'total_words': len(total_text.split()),
                    'full_text': total_text
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'filename': os.path.basename(pdf_path)
            }

    @staticmethod
    def analyze_pdf_structure(pdf_path: str, use_llm: bool = False, llm_analyzer = None) -> Dict[str, Any]:
        """
        Analyze PDF structure and content patterns with optional LLM enhancement

        Args:
            pdf_path: Path to PDF file
            use_llm: Whether to use LLM for structural analysis
            llm_analyzer: LLM analyzer instance (GPTContentGenerator)

        Returns:
            Dictionary with detailed structure analysis
        """
        extraction = PDFExtractor.extract_text_from_pdf(pdf_path)

        if not extraction['success']:
            return extraction

        pages = extraction['pages']
        full_text = extraction['full_text']

        # Basic analysis
        basic_analysis = {
            'avg_words_per_page': sum(p['word_count'] for p in pages) / len(pages) if pages else 0,
            'longest_page': max(pages, key=lambda p: p['word_count']) if pages else None,
            'shortest_page': min(pages, key=lambda p: p['word_count']) if pages else None,
            'content_type': PDFExtractor._detect_content_type(full_text),
            'has_structure': PDFExtractor._detect_structure(full_text)
        }

        # Enhanced structural analysis
        structural_elements = PDFExtractor._analyze_structural_elements(full_text)
        content_components = PDFExtractor._analyze_content_components(full_text)

        analysis = {
            **basic_analysis,
            'structural_elements': structural_elements,
            'content_components': content_components
        }

        # LLM-based deep analysis (optional)
        if use_llm and llm_analyzer:
            llm_analysis = PDFExtractor._llm_structural_analysis(full_text, llm_analyzer)
            if llm_analysis.get('success'):
                analysis['llm_analysis'] = llm_analysis['analysis']

        return {
            **extraction,
            'analysis': analysis
        }

    @staticmethod
    def _detect_content_type(text: str) -> str:
        """Detect the type of content (report, invoice, letter, etc.)"""
        text_lower = text.lower()

        if 'invoice' in text_lower or 'bill' in text_lower:
            return 'invoice'
        elif 'report' in text_lower or 'analysis' in text_lower:
            return 'report'
        elif 'dear' in text_lower or 'sincerely' in text_lower:
            return 'letter'
        elif 'contract' in text_lower or 'agreement' in text_lower:
            return 'contract'
        else:
            return 'document'

    @staticmethod
    def _detect_structure(text: str) -> bool:
        """Detect if document has structured sections"""
        # Simple heuristic: check for section markers
        markers = ['chapter', 'section', '1.', '2.', 'introduction', 'conclusion']
        text_lower = text.lower()
        return any(marker in text_lower for marker in markers)

    @staticmethod
    def _analyze_structural_elements(text: str) -> Dict[str, Any]:
        """
        Analyze structural elements in the document

        Returns detailed breakdown of document structure
        """
        import re

        lines = text.split('\n')

        # Detect headings (all caps, short lines, ending with colon)
        headings = []
        for line in lines:
            stripped = line.strip()
            if stripped:
                # All caps heading
                if stripped.isupper() and len(stripped) < 80:
                    headings.append({'type': 'uppercase', 'text': stripped})
                # Numbered heading (1., 1.1, etc.)
                elif re.match(r'^\d+(\.\d+)*\.?\s+', stripped):
                    headings.append({'type': 'numbered', 'text': stripped})
                # Colon heading
                elif stripped.endswith(':') and len(stripped) < 100:
                    headings.append({'type': 'colon', 'text': stripped})

        # Detect lists
        bullet_points = len(re.findall(r'^\s*[•\-\*]\s+', text, re.MULTILINE))
        numbered_lists = len(re.findall(r'^\s*\d+[\)\.]\s+', text, re.MULTILINE))

        # Detect tables (simple heuristic: lines with multiple | or tabs)
        table_lines = len([l for l in lines if l.count('|') > 2 or l.count('\t') > 2])

        # Detect sections
        section_markers = re.findall(
            r'(chapter|section|part|appendix)\s+\d+',
            text,
            re.IGNORECASE
        )

        # Paragraph analysis
        paragraphs = [p for p in text.split('\n\n') if p.strip()]
        avg_paragraph_length = sum(len(p.split()) for p in paragraphs) / len(paragraphs) if paragraphs else 0

        return {
            'has_headings': len(headings) > 0,
            'heading_count': len(headings),
            'heading_types': {
                'uppercase': len([h for h in headings if h['type'] == 'uppercase']),
                'numbered': len([h for h in headings if h['type'] == 'numbered']),
                'colon': len([h for h in headings if h['type'] == 'colon'])
            },
            'has_bullet_lists': bullet_points > 0,
            'bullet_point_count': bullet_points,
            'has_numbered_lists': numbered_lists > 0,
            'numbered_list_count': numbered_lists,
            'has_tables': table_lines > 3,
            'table_line_count': table_lines,
            'section_count': len(section_markers),
            'paragraph_count': len(paragraphs),
            'avg_paragraph_length': round(avg_paragraph_length, 1),
            'headings_sample': headings[:5]  # First 5 headings as samples
        }

    @staticmethod
    def _analyze_content_components(text: str) -> Dict[str, Any]:
        """
        Analyze content components and patterns

        Returns breakdown of content types and entities
        """
        import re

        # Detect dates
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{2,4}',  # MM/DD/YYYY
            r'\d{4}-\d{2}-\d{2}',         # YYYY-MM-DD
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}'  # Month DD, YYYY
        ]
        dates_found = sum(len(re.findall(pattern, text, re.IGNORECASE)) for pattern in date_patterns)

        # Detect numbers and amounts
        currency_amounts = len(re.findall(r'\$\s?\d+(?:,\d{3})*(?:\.\d{2})?', text))
        percentages = len(re.findall(r'\d+(?:\.\d+)?%', text))
        general_numbers = len(re.findall(r'\b\d+(?:,\d{3})*(?:\.\d+)?\b', text))

        # Detect emails and URLs
        emails = len(re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text))
        urls = len(re.findall(r'https?://[^\s]+', text))

        # Detect names (capitalized words, heuristic)
        capitalized_words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', text)
        potential_names = len(set(capitalized_words))

        # Detect addresses (simple heuristic)
        addresses = len(re.findall(r'\d+\s+[A-Z][a-z]+\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)', text))

        # Detect phone numbers
        phone_numbers = len(re.findall(r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text))

        # Content density
        words = text.split()
        unique_words = len(set(word.lower() for word in words))
        lexical_diversity = unique_words / len(words) if words else 0

        # Detect special formatting
        has_bold_markers = '**' in text or '__' in text
        has_italic_markers = '*' in text or '_' in text
        has_code_blocks = '```' in text or '`' in text

        return {
            'dates_found': dates_found,
            'currency_amounts': currency_amounts,
            'percentages': percentages,
            'numbers_found': general_numbers,
            'emails_found': emails,
            'urls_found': urls,
            'potential_names': potential_names,
            'addresses_found': addresses,
            'phone_numbers': phone_numbers,
            'lexical_diversity': round(lexical_diversity, 3),
            'has_formatting_markers': has_bold_markers or has_italic_markers or has_code_blocks,
            'content_density': {
                'total_words': len(words),
                'unique_words': unique_words,
                'avg_word_length': round(sum(len(w) for w in words) / len(words), 1) if words else 0
            }
        }

    @staticmethod
    def _llm_structural_analysis(text: str, llm_analyzer) -> Dict[str, Any]:
        """
        Use LLM to perform deep structural analysis

        Args:
            text: Document text
            llm_analyzer: GPTContentGenerator instance

        Returns:
            Dictionary with LLM analysis results
        """
        # Truncate text for analysis (keep first 2000 chars)
        sample = text[:2000] if len(text) > 2000 else text

        prompt = f"""Analyze the following document excerpt and provide a detailed structural analysis.

Document Excerpt:
---
{sample}
---

Provide a JSON response with the following analysis:
{{
    "document_type": "<type: report, invoice, letter, contract, article, etc.>",
    "primary_purpose": "<main purpose of the document>",
    "structure_pattern": "<how the document is organized>",
    "key_sections": ["<list of main sections>"],
    "writing_style": "<formal, informal, technical, conversational, etc.>",
    "tone": "<professional, casual, persuasive, informative, etc.>",
    "formatting_features": ["<list of formatting elements observed>"],
    "content_patterns": ["<recurring patterns in the content>"],
    "data_elements": ["<types of data present: dates, amounts, names, etc.>"],
    "layout_characteristics": "<description of layout style>",
    "audience": "<intended audience>",
    "complexity_level": "<simple, moderate, complex>",
    "special_features": ["<any unique or notable features>"]
}}

Respond with ONLY the JSON object, no additional text."""

        try:
            response = llm_analyzer._call_gpt_api(prompt)

            if response['success']:
                # Parse JSON response
                content = response['content'].strip()
                # Remove markdown code blocks if present
                if content.startswith('```'):
                    content = content.split('```')[1]
                    if content.startswith('json'):
                        content = content[4:]
                    content = content.strip()

                analysis = json.loads(content)

                return {
                    'success': True,
                    'analysis': analysis
                }
            else:
                return {
                    'success': False,
                    'error': response.get('error', 'LLM analysis failed')
                }

        except Exception as e:
            return {
                'success': False,
                'error': f'LLM structural analysis failed: {str(e)}'
            }


class GPTContentGenerator:
    """Generate synthetic content using GPT API"""

    def __init__(
        self,
        api_key: str = None,
        api_endpoint: str = None,
        model: str = "gpt-4o-mini"
    ):
        """
        Initialize GPT content generator

        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY env variable)
            api_endpoint: Custom API endpoint (or set OPENAI_API_ENDPOINT env variable)
            model: GPT model to use (default: gpt-4o-mini - reliable and fast)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY', 'YOUR_OPENAI_API_KEY_HERE')
        self.api_endpoint = api_endpoint or os.getenv('OPENAI_API_ENDPOINT', 'https://api.openai.com/v1/chat/completions')
        self.model = model
        logger.info(f"Initialized GPT generator with model: {self.model}")

    def generate_synthetic_content(
        self,
        sample_text: str,
        content_type: str = 'document',
        num_pages: int = 1,
        style_instructions: str = None,
        structural_analysis: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate synthetic content similar to sample with structural awareness

        Args:
            sample_text: Sample text to mimic
            content_type: Type of content (report, invoice, letter, etc.)
            num_pages: Number of pages to generate
            style_instructions: Additional style instructions
            structural_analysis: Detailed structural analysis from extraction

        Returns:
            Dictionary with generated content
        """
        try:
            # Build prompt with structural awareness
            prompt = self._build_generation_prompt(
                sample_text,
                content_type,
                num_pages,
                style_instructions,
                structural_analysis
            )

            # Call GPT API
            response = self._call_gpt_api(prompt)

            if response['success']:
                return {
                    'success': True,
                    'content': response['content'],
                    'model': self.model,
                    'content_type': content_type
                }
            else:
                return {
                    'success': False,
                    'error': response.get('error', 'Unknown error')
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _build_generation_prompt(
        self,
        sample_text: str,
        content_type: str,
        num_pages: int,
        style_instructions: str = None,
        structural_analysis: Dict[str, Any] = None
    ) -> str:
        """Build GPT prompt for content generation with structural awareness"""

        # Truncate sample if too long (keep first 3000 chars as reference)
        sample_truncated = sample_text[:3000] if len(sample_text) > 3000 else sample_text

        prompt = f"""You are an advanced synthetic document generator. Your task is to create a NEW document that maintains the STRUCTURE and STYLE of the sample, but with completely different content.

Sample Document Content:
---
{sample_truncated}
---
"""

        # Add structural guidance if available
        if structural_analysis:
            prompt += "\n=== STRUCTURAL REQUIREMENTS ===\n"

            struct_elem = structural_analysis.get('structural_elements', {})
            content_comp = structural_analysis.get('content_components', {})
            llm_analysis = structural_analysis.get('llm_analysis', {})

            # Add LLM analysis insights
            if llm_analysis:
                prompt += f"\nDocument Type: {llm_analysis.get('document_type', content_type)}\n"
                prompt += f"Writing Style: {llm_analysis.get('writing_style', 'professional')}\n"
                prompt += f"Tone: {llm_analysis.get('tone', 'formal')}\n"

                if llm_analysis.get('key_sections'):
                    prompt += f"Key Sections to Include: {', '.join(llm_analysis['key_sections'])}\n"

                if llm_analysis.get('formatting_features'):
                    prompt += f"Formatting Features: {', '.join(llm_analysis['formatting_features'])}\n"

            # Add structural elements
            if struct_elem.get('has_headings'):
                prompt += f"\n- Include {struct_elem['heading_count']} headings (types: "
                heading_types = struct_elem.get('heading_types', {})
                types_desc = []
                if heading_types.get('uppercase', 0) > 0:
                    types_desc.append(f"{heading_types['uppercase']} uppercase")
                if heading_types.get('numbered', 0) > 0:
                    types_desc.append(f"{heading_types['numbered']} numbered")
                if heading_types.get('colon', 0) > 0:
                    types_desc.append(f"{heading_types['colon']} with colons")
                prompt += ", ".join(types_desc) + ")\n"

            if struct_elem.get('has_bullet_lists'):
                prompt += f"- Include approximately {struct_elem['bullet_point_count']} bullet points\n"

            if struct_elem.get('has_numbered_lists'):
                prompt += f"- Include approximately {struct_elem['numbered_list_count']} numbered list items\n"

            if struct_elem.get('has_tables'):
                prompt += f"- Include table-like structures (observed {struct_elem['table_line_count']} table lines)\n"

            prompt += f"- Create approximately {struct_elem.get('paragraph_count', 5)} paragraphs\n"
            prompt += f"- Average paragraph length: ~{struct_elem.get('avg_paragraph_length', 50)} words\n"

            # Add content component guidance
            if content_comp.get('dates_found', 0) > 0:
                prompt += f"\n- Include approximately {content_comp['dates_found']} dates (use realistic but different dates)\n"

            if content_comp.get('currency_amounts', 0) > 0:
                prompt += f"- Include approximately {content_comp['currency_amounts']} currency amounts\n"

            if content_comp.get('percentages', 0) > 0:
                prompt += f"- Include approximately {content_comp['percentages']} percentages\n"

            if content_comp.get('potential_names', 0) > 0:
                prompt += f"- Include approximately {content_comp['potential_names']} person/organization names (completely different from original)\n"

            if content_comp.get('emails_found', 0) > 0:
                prompt += f"- Include {content_comp['emails_found']} email addresses (fictional)\n"

            if content_comp.get('phone_numbers', 0) > 0:
                prompt += f"- Include {content_comp['phone_numbers']} phone numbers (fictional)\n"

            if content_comp.get('addresses_found', 0) > 0:
                prompt += f"- Include {content_comp['addresses_found']} addresses (fictional)\n"

            prompt += f"\nLexical Complexity: Maintain similar vocabulary diversity (original: {content_comp.get('lexical_diversity', 0.5):.2f})\n"

        prompt += f"""
=== GENERATION REQUIREMENTS ===
- Generate approximately {num_pages} page(s) worth of content (roughly {num_pages * 400} words)
- Use COMPLETELY DIFFERENT specific details (names, numbers, dates, locations, etc.)
- Maintain the SAME document structure and flow
- Keep the SAME tone, formality level, and writing style
- Make it realistic, coherent, and professional
- DO NOT copy any actual content from the sample - all details must be NEW

=== CRITICAL FORMATTING INSTRUCTIONS ===

⚠️ TABLES ARE MANDATORY - If the sample contains tables, YOU MUST include tables in your output!

For tables and structured data (THIS IS REQUIRED):
1. ALWAYS use pipe (|) separators for table columns
2. Put each row on a new line
3. First row MUST be column headers
4. Align columns consistently

EXAMPLE TABLE FORMAT (you MUST use this exact format):
Item No. | Description | Quantity | Unit Price | Total
1 | Laptop Computer Dell XPS 15 | 3 | $1,200.00 | $3,600.00
2 | Wireless Mouse Logitech MX | 5 | $45.00 | $225.00
3 | USB-C Cable 6ft | 10 | $15.00 | $150.00

For invoices/purchase orders specifically:
- Include a table with AT LEAST these columns: Item/Description, Quantity, Price, Total
- Add 3-5 line items minimum
- Include subtotal, tax, and total rows if in original

For headers and sections:
- Use ALL CAPS for major section headers (e.g., "PURCHASE ORDER", "INVOICE")
- Use colons for field labels (e.g., "Date:", "Invoice No.:", "Bill To:")
- Keep form-like structure with fields and values

For lists:
- Use bullet points (•) or dashes (-) for unordered lists
- Use numbers (1., 2., etc.) for ordered lists
"""

        if style_instructions:
            prompt += f"\n=== ADDITIONAL INSTRUCTIONS ===\n{style_instructions}\n"

        # Add specific invoice/purchase order template if detected
        if 'invoice' in content_type.lower() or 'purchase' in content_type.lower() or 'order' in content_type.lower():
            prompt += """
=== EXACT OUTPUT FORMAT FOR PURCHASE ORDERS/INVOICES ===

You MUST follow this EXACT structure. Do not deviate from this format:

```
PURCHASE ORDER

Date: [DATE] Requisition No.: [NUMBER] P.O. No. (Accounting Only): [PO-NUMBER]

Ship To: [COMPANY NAME]
[ADDRESS]
Project No.: [NUMBER]

Client Name: [X] [NAME] [ ] Other:

Job Name: [JOB NAME]
Job Location: [LOCATION]
Project Manager: [NAME]

Vendor Name: [VENDOR]
Address: [VENDOR ADDRESS]
Tel: [PHONE] Fax: [FAX]
E-Mail: [EMAIL]

Date Item Needed: [DATE]
Order to be placed with: [NAME]

Item No. | Item Description | Replacement Part For | Department | Vendor Stock No. | Qty. | Unit Cost | Total Cost
1 | [PRODUCT NAME AND SPECS] | [PROJECT/DEPT] | [DEPT] | [STOCK#] | [QTY] | $[PRICE] | $[TOTAL]
2 | [PRODUCT NAME AND SPECS] | [PROJECT/DEPT] | [DEPT] | [STOCK#] | [QTY] | $[PRICE] | $[TOTAL]
3 | [PRODUCT NAME AND SPECS] | [PROJECT/DEPT] | [DEPT] | [STOCK#] | [QTY] | $[PRICE] | $[TOTAL]

[COMPANY NAME] • [ADDRESS]
Tel: [PHONE] • Fax: [FAX] • Email: [EMAIL]

Prepared By: [NAME]

Subtotal: $[AMOUNT]
Sales Tax: $[AMOUNT]
Shipping Charge: $[AMOUNT]
Estimated Total: $[AMOUNT]
```

🚨 CRITICAL REQUIREMENTS:
1. Match the EXACT field layout from the original
2. Include ALL columns from the original table
3. Add 3-5 realistic line items
4. Use completely different company names, addresses, products, but SAME structure
5. Make amounts realistic and add up correctly
"""
        else:
            prompt += """
=== OUTPUT FORMAT ===
Generate the complete synthetic document content now.

🚨 CRITICAL: If the original document has a table (items, line items, data rows), you MUST include a properly formatted table using pipe (|) separators.

Output text only, with tables formatted using pipes (|) as shown above.
"""

        return prompt

    def _call_gpt_api(self, prompt: str, retry_count: int = 3) -> Dict[str, Any]:
        """
        Call GPT API to generate content with retry logic and validation

        Args:
            prompt: The prompt to send to GPT
            retry_count: Number of retries on failure

        Returns:
            Dictionary with success status and content/error
        """
        # Check if using placeholder API key
        if self.api_key == 'YOUR_OPENAI_API_KEY_HERE' or not self.api_key:
            return {
                'success': False,
                'error': 'OpenAI API key not configured. Please set OPENAI_API_KEY environment variable or provide api_key parameter.'
            }

        # Determine timeout and model parameters
        is_gpt5_or_reasoning = 'gpt-5' in self.model.lower() or 'o1' in self.model.lower() or 'o3' in self.model.lower()
        timeout = 120 if is_gpt5_or_reasoning else 60  # GPT-5 is slower, needs more time

        for attempt in range(retry_count):
            try:
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                }

                payload = {
                    'model': self.model,
                    'messages': [
                        {
                            'role': 'system',
                            'content': 'You are a professional document generator that creates synthetic business documents. You MUST follow formatting instructions exactly, especially when creating tables. Always use pipe (|) separators for table columns. NEVER return empty content - always generate a complete document.'
                        },
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ]
                }

                # GPT-5 models have different parameter requirements than GPT-4
                if is_gpt5_or_reasoning:
                    # GPT-5 and reasoning models use max_completion_tokens and only support temperature=1
                    payload['max_completion_tokens'] = 4000
                    # Don't set temperature - use default (1) for GPT-5
                else:
                    # GPT-4 and earlier use max_tokens and support custom temperature
                    payload['max_tokens'] = 4000
                    payload['temperature'] = 0.7

                if attempt > 0:
                    logger.warning(f"Retrying GPT API call", extra={
                        'extra_data': {
                            'attempt': attempt + 1,
                            'max_retries': retry_count,
                            'model': self.model
                        }
                    })
                    logger.info(f"Retry attempt {attempt + 1}/{retry_count}...")

                logger.debug(f"Calling GPT API", extra={
                    'extra_data': {
                        'model': self.model,
                        'timeout': timeout,
                        'attempt': attempt + 1
                    }
                })

                response = requests.post(
                    self.api_endpoint,
                    headers=headers,
                    json=payload,
                    timeout=timeout
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data['choices'][0]['message']['content'].strip()

                    # Validate content is not empty
                    if not content or len(content) < 50:
                        logger.warning(f"GPT returned empty/short content", extra={
                            'extra_data': {
                                'content_length': len(content),
                                'model': self.model,
                                'attempt': attempt + 1
                            }
                        })
                        logger.warning(f"GPT returned empty or very short content ({len(content)} chars)")
                        if attempt < retry_count - 1:
                            continue  # Retry
                        else:
                            return {
                                'success': False,
                                'error': f'GPT returned empty content after {retry_count} attempts'
                            }

                    # Debug: Check if content has tables
                    has_tables = '|' in content
                    table_lines = [line for line in content.split('\n') if '|' in line] if has_tables else []

                    logger.info(f"GPT API success", extra={
                        'extra_data': {
                            'model': self.model,
                            'content_length': len(content),
                            'has_tables': has_tables,
                            'table_lines': len(table_lines),
                            'attempt': attempt + 1
                        }
                    })
                    logger.info(f"GPT Response: {len(content)} chars, Has tables: {has_tables}")
                    if has_tables:
                        logger.debug(f"Found {len(table_lines)} lines with table data")

                    return {
                        'success': True,
                        'content': content
                    }
                else:
                    error_msg = f'API returned status {response.status_code}: {response.text}'
                    logger.error(f"GPT API error", extra={
                        'extra_data': {
                            'status_code': response.status_code,
                            'model': self.model,
                            'attempt': attempt + 1,
                            'error': response.text[:200]  # First 200 chars
                        }
                    })
                    logger.error(f"API Error: {error_msg}")
                    if attempt < retry_count - 1:
                        continue  # Retry
                    else:
                        return {
                            'success': False,
                            'error': error_msg
                        }

            except requests.exceptions.Timeout:
                error_msg = f'Request timed out after {timeout} seconds'
                logger.error(f"GPT API timeout", extra={
                    'extra_data': {
                        'timeout': timeout,
                        'model': self.model,
                        'attempt': attempt + 1
                    }
                })
                logger.error(f"Timeout Error: {error_msg}")
                if attempt < retry_count - 1:
                    continue  # Retry
                else:
                    return {
                        'success': False,
                        'error': error_msg
                    }

            except Exception as e:
                error_msg = f'API call failed: {str(e)}'
                logger.error(f"GPT API exception", exc_info=True, extra={
                    'extra_data': {
                        'model': self.model,
                        'attempt': attempt + 1,
                        'error': str(e)
                    }
                })
                logger.error(f"Exception: {error_msg}")
                if attempt < retry_count - 1:
                    continue  # Retry
                else:
                    return {
                        'success': False,
                        'error': error_msg
                    }

        # Should not reach here, but just in case
        return {
            'success': False,
            'error': f'Failed after {retry_count} attempts'
        }


class PDFSynthesizer:
    """Create synthetic PDF documents with structure preservation"""

    @staticmethod
    def create_structured_pdf(
        text: str,
        output_path: str,
        structural_analysis: Dict[str, Any] = None,
        title: str = None,
        author: str = 'DataForge Synthetic Generator',
        page_size: tuple = letter
    ) -> Dict[str, Any]:
        """
        Create a PDF with preserved structure (tables, forms, headers)

        Args:
            text: Generated synthetic text
            output_path: Path to save PDF
            structural_analysis: Structural analysis from extraction
            title: Document title
            author: Document author
            page_size: Page size

        Returns:
            Dictionary with success status and file info
        """
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Parse text into structured components
            components = PDFSynthesizer._parse_text_structure(text, structural_analysis)

            # Create PDF with structure
            doc = SimpleDocTemplate(
                output_path,
                pagesize=page_size,
                topMargin=0.5*inch,
                bottomMargin=0.5*inch,
                leftMargin=0.75*inch,
                rightMargin=0.75*inch
            )

            # Build styled story
            story = PDFSynthesizer._build_structured_story(components, title, structural_analysis)

            # Build PDF
            doc.build(story)

            # Get file info
            file_size = os.path.getsize(output_path)

            return {
                'success': True,
                'output_path': output_path,
                'file_size': file_size,
                'filename': os.path.basename(output_path)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def create_pdf_from_text(
        text: str,
        output_path: str,
        title: str = None,
        author: str = 'DataForge Synthetic Generator',
        page_size: tuple = letter
    ) -> Dict[str, Any]:
        """
        Create a PDF document from text content

        Args:
            text: Text content to put in PDF
            output_path: Path to save PDF
            title: Document title
            author: Document author
            page_size: Page size (letter, A4, etc.)

        Returns:
            Dictionary with success status and file info
        """
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Create PDF
            doc = SimpleDocTemplate(
                output_path,
                pagesize=page_size,
                topMargin=0.75*inch,
                bottomMargin=0.75*inch,
                leftMargin=1*inch,
                rightMargin=1*inch
            )

            # Styles
            styles = getSampleStyleSheet()

            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor='#1a1a1a',
                spaceAfter=20,
                alignment=TA_CENTER
            )

            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['BodyText'],
                fontSize=11,
                leading=14,
                alignment=TA_JUSTIFY,
                spaceAfter=12
            )

            # Build content
            story = []

            # Add title if provided
            if title:
                story.append(Paragraph(title, title_style))
                story.append(Spacer(1, 0.3*inch))

            # Split text into paragraphs
            paragraphs = text.split('\n\n')

            for para_text in paragraphs:
                if para_text.strip():
                    # Check if it's a heading (simple heuristic)
                    if len(para_text) < 100 and para_text.strip().endswith(':'):
                        story.append(Paragraph(para_text.strip(), styles['Heading2']))
                    else:
                        # Regular paragraph
                        story.append(Paragraph(para_text.strip(), body_style))
                    story.append(Spacer(1, 0.1*inch))

            # Build PDF
            doc.build(story)

            # Get file info
            file_size = os.path.getsize(output_path)

            return {
                'success': True,
                'output_path': output_path,
                'file_size': file_size,
                'filename': os.path.basename(output_path)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def _parse_text_structure(text: str, structural_analysis: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Parse text into structured components (headers, tables, paragraphs, lists)

        Returns:
            List of component dictionaries with type and content
        """
        import re

        components = []
        lines = text.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if not line:
                i += 1
                continue

            # Detect table rows (contains multiple | or tabs)
            if '|' in line or '\t' in line:
                # Collect table rows
                table_rows = []
                while i < len(lines) and ('|' in lines[i] or '\t' in lines[i] or lines[i].strip() == ''):
                    if lines[i].strip():
                        # Split by | or tab
                        if '|' in lines[i]:
                            cells = [c.strip() for c in lines[i].split('|') if c.strip()]
                        else:
                            cells = [c.strip() for c in lines[i].split('\t') if c.strip()]
                        if cells:
                            table_rows.append(cells)
                    i += 1

                if table_rows:
                    components.append({
                        'type': 'table',
                        'data': table_rows
                    })
                continue

            # Detect headers (all caps, short, or ends with colon)
            if line.isupper() and len(line) < 100:
                components.append({
                    'type': 'header',
                    'level': 1,
                    'text': line
                })
                i += 1
                continue

            # Detect numbered headings
            if re.match(r'^\d+(\.\d+)*\.?\s+[A-Z]', line):
                components.append({
                    'type': 'header',
                    'level': 2,
                    'text': line
                })
                i += 1
                continue

            # Detect colon headers
            if line.endswith(':') and len(line) < 100 and not re.search(r'\d{1,2}:\d{2}', line):
                components.append({
                    'type': 'header',
                    'level': 2,
                    'text': line
                })
                i += 1
                continue

            # Detect bullet points
            if re.match(r'^\s*[•\-\*]\s+', line):
                list_items = []
                while i < len(lines) and re.match(r'^\s*[•\-\*]\s+', lines[i]):
                    item_text = re.sub(r'^\s*[•\-\*]\s+', '', lines[i])
                    list_items.append(item_text)
                    i += 1

                components.append({
                    'type': 'bullet_list',
                    'items': list_items
                })
                continue

            # Detect numbered lists
            if re.match(r'^\s*\d+[\)\.]\s+', line):
                list_items = []
                while i < len(lines) and re.match(r'^\s*\d+[\)\.]\s+', lines[i]):
                    item_text = re.sub(r'^\s*\d+[\)\.]\s+', '', lines[i])
                    list_items.append(item_text)
                    i += 1

                components.append({
                    'type': 'numbered_list',
                    'items': list_items
                })
                continue

            # Regular paragraph
            para_lines = [line]
            i += 1

            # Collect continuation lines for paragraph
            while i < len(lines) and lines[i].strip() and not any([
                lines[i].strip().isupper() and len(lines[i].strip()) < 100,
                re.match(r'^\d+(\.\d+)*\.?\s+[A-Z]', lines[i]),
                lines[i].strip().endswith(':') and len(lines[i].strip()) < 100,
                re.match(r'^\s*[•\-\*]\s+', lines[i]),
                re.match(r'^\s*\d+[\)\.]\s+', lines[i]),
                '|' in lines[i] or '\t' in lines[i]
            ]):
                para_lines.append(lines[i].strip())
                i += 1

            components.append({
                'type': 'paragraph',
                'text': ' '.join(para_lines)
            })

        return components

    @staticmethod
    def _build_structured_story(components: List[Dict[str, Any]], title: str = None,
                                structural_analysis: Dict[str, Any] = None) -> List:
        """
        Build ReportLab story from structured components

        Returns:
            List of ReportLab flowables
        """
        styles = getSampleStyleSheet()

        # Custom styles
        header1_style = ParagraphStyle(
            'Header1',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=12,
            spaceBefore=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )

        header2_style = ParagraphStyle(
            'Header2',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#2a2a2a'),
            spaceAfter=8,
            spaceBefore=10,
            fontName='Helvetica-Bold'
        )

        body_style = ParagraphStyle(
            'Body',
            parent=styles['BodyText'],
            fontSize=10,
            leading=13,
            alignment=TA_LEFT,
            spaceAfter=8
        )

        list_style = ParagraphStyle(
            'ListItem',
            parent=styles['BodyText'],
            fontSize=10,
            leading=13,
            leftIndent=20,
            spaceAfter=4
        )

        story = []

        # Add title if provided
        if title:
            title_style = ParagraphStyle(
                'Title',
                parent=styles['Title'],
                fontSize=18,
                textColor=colors.HexColor('#000000'),
                spaceAfter=20,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )
            story.append(Paragraph(title, title_style))
            story.append(Spacer(1, 0.2*inch))

        # Build components
        for component in components:
            comp_type = component['type']

            if comp_type == 'header':
                level = component.get('level', 1)
                text = component['text']
                style = header1_style if level == 1 else header2_style
                story.append(Paragraph(text, style))

            elif comp_type == 'paragraph':
                text = component['text']
                if text:
                    story.append(Paragraph(text, body_style))

            elif comp_type == 'bullet_list':
                for item in component['items']:
                    story.append(Paragraph(f"• {item}", list_style))
                story.append(Spacer(1, 0.1*inch))

            elif comp_type == 'numbered_list':
                for idx, item in enumerate(component['items'], 1):
                    story.append(Paragraph(f"{idx}. {item}", list_style))
                story.append(Spacer(1, 0.1*inch))

            elif comp_type == 'table':
                table_data = component['data']

                # Create table
                table = Table(table_data, repeatRows=1)

                # Style table
                table_style = TableStyle([
                    # Header row
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a90e2')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('TOPPADDING', (0, 0), (-1, 0), 8),

                    # Data rows
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('TOPPADDING', (0, 1), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 1), (-1, -1), 4),

                    # Grid
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('BOX', (0, 0), (-1, -1), 1, colors.black),

                    # Alternating row colors
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')])
                ])

                table.setStyle(table_style)
                story.append(table)
                story.append(Spacer(1, 0.15*inch))

        return story


def generate_synthetic_pdfs_from_samples(
    sample_pdf_folder: str,
    output_folder: str,
    num_pdfs_per_sample: int = 1,
    gpt_api_key: str = None,
    gpt_endpoint: str = None,
    progress_callback = None
) -> Dict[str, Any]:
    """
    Generate synthetic PDFs from a folder of sample PDFs

    Args:
        sample_pdf_folder: Folder containing sample PDF files
        output_folder: Folder to save generated PDFs
        num_pdfs_per_sample: Number of synthetic PDFs to generate per sample
        gpt_api_key: OpenAI API key
        gpt_endpoint: Custom GPT endpoint
        progress_callback: Callback function for progress updates

    Returns:
        Dictionary with generation results
    """
    results = {
        'success': True,
        'samples_processed': 0,
        'pdfs_generated': 0,
        'failed': 0,
        'generated_files': [],
        'errors': []
    }

    try:
        # Create output folder
        os.makedirs(output_folder, exist_ok=True)

        # Get sample PDFs
        sample_pdfs = [
            os.path.join(sample_pdf_folder, f)
            for f in os.listdir(sample_pdf_folder)
            if f.lower().endswith('.pdf')
        ]

        if not sample_pdfs:
            logger.error(f"No PDF files found", extra={'extra_data': {'folder': sample_pdf_folder}})
            return {
                'success': False,
                'error': f'No PDF files found in {sample_pdf_folder}'
            }

        logger.info(f"Starting PDF generation", extra={
            'extra_data': {
                'sample_count': len(sample_pdfs),
                'num_pdfs_per_sample': num_pdfs_per_sample,
                'output_folder': output_folder
            }
        })
        logger.info(f"Found {len(sample_pdfs)} sample PDF(s)")

        # Initialize generators
        extractor = PDFExtractor()
        gpt_generator = GPTContentGenerator(api_key=gpt_api_key, api_endpoint=gpt_endpoint)
        synthesizer = PDFSynthesizer()

        # Process each sample
        for idx, sample_path in enumerate(sample_pdfs):
            sample_name = os.path.basename(sample_path)
            logger.info(f"Processing sample PDF", extra={
                'extra_data': {
                    'sample_index': idx + 1,
                    'total_samples': len(sample_pdfs),
                    'sample_name': sample_name
                }
            })
            logger.info(f"Processing sample {idx + 1}/{len(sample_pdfs)}: {sample_name}")

            if progress_callback:
                progress_callback(idx / len(sample_pdfs) * 100, f"Processing {sample_name}")

            # Extract content with LLM-enhanced analysis
            logger.debug("Analyzing PDF structure...")
            logger.debug("Analyzing PDF structure...")
            extraction = extractor.analyze_pdf_structure(
                sample_path,
                use_llm=True,  # Enable LLM structural analysis
                llm_analyzer=gpt_generator
            )

            if not extraction['success']:
                logger.error(f"PDF extraction failed", extra={
                    'extra_data': {
                        'sample_name': sample_name,
                        'error': extraction.get('error')
                    }
                })
                results['failed'] += 1
                results['errors'].append(f"Failed to extract {sample_name}: {extraction.get('error')}")
                continue

            results['samples_processed'] += 1

            # Log structural analysis
            analysis = extraction['analysis']
            logger.info(f"Document type: {analysis.get('content_type', 'unknown')}")
            if 'llm_analysis' in analysis:
                llm_info = analysis['llm_analysis']
                logger.info(f"LLM detected: {llm_info.get('document_type', 'N/A')} - {llm_info.get('primary_purpose', 'N/A')}")
            logger.info(f"Structure: {analysis['structural_elements']['heading_count']} headings, "
                  f"{analysis['structural_elements']['paragraph_count']} paragraphs")

            # Generate synthetic PDFs
            for gen_idx in range(num_pdfs_per_sample):
                logger.info(f"Generating synthetic PDF {gen_idx + 1}/{num_pdfs_per_sample}...")

                # Generate content with GPT using structural analysis
                gen_result = gpt_generator.generate_synthetic_content(
                    sample_text=extraction['full_text'],
                    content_type=extraction['analysis']['content_type'],
                    num_pages=extraction['total_pages'],
                    style_instructions=f"Maintain similar professional tone and structure",
                    structural_analysis=extraction['analysis']  # Pass structural analysis
                )

                if not gen_result['success']:
                    results['failed'] += 1
                    error_msg = gen_result.get('error', 'Unknown error')
                    logger.error(f"GPT generation failed: {error_msg}")
                    results['errors'].append(f"GPT generation failed for {sample_name}: {error_msg}")
                    continue

                logger.info("GPT content generated successfully")

                # Create PDF with structure preservation
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"synthetic_{os.path.splitext(sample_name)[0]}_{gen_idx + 1}_{timestamp}.pdf"
                output_path = os.path.join(output_folder, output_filename)

                # Use structured PDF creation for better layout preservation
                pdf_result = synthesizer.create_structured_pdf(
                    text=gen_result['content'],
                    output_path=output_path,
                    structural_analysis=extraction['analysis'],
                    title=f"Synthetic {extraction['analysis']['content_type'].title()}"
                )

                if pdf_result['success']:
                    results['pdfs_generated'] += 1
                    results['generated_files'].append({
                        'filename': output_filename,
                        'path': output_path,
                        'size': pdf_result['file_size'],
                        'source': sample_name
                    })
                    logger.info(f"Generated: {output_filename}")
                else:
                    results['failed'] += 1
                    results['errors'].append(f"PDF creation failed: {pdf_result.get('error')}")

        if progress_callback:
            progress_callback(100, "Generation complete")

        return results

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
