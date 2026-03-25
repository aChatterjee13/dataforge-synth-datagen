export async function generateValidationReport(validation: any, jobId: string): Promise<void> {
  const jsPDFModule = await import('jspdf');
  const jsPDF = jsPDFModule.default;
  const html2canvasModule = await import('html2canvas');
  const html2canvas = html2canvasModule.default;

  const doc = new jsPDF('p', 'mm', 'a4');
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 20;
  const contentWidth = pageWidth - margin * 2;
  let yPos = margin;

  const addNewPageIfNeeded = (requiredSpace: number) => {
    if (yPos + requiredSpace > pageHeight - margin) {
      doc.addPage();
      yPos = margin;
    }
  };

  // --- Title ---
  doc.setFontSize(22);
  doc.setFont('helvetica', 'bold');
  doc.text('DataForge - Validation Report', pageWidth / 2, yPos, { align: 'center' });
  yPos += 12;

  // --- Job ID and Date ---
  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');
  doc.text(`Job ID: ${jobId}`, margin, yPos);
  yPos += 6;
  doc.text(`Date: ${new Date().toLocaleString()}`, margin, yPos);
  yPos += 12;

  // --- Divider ---
  doc.setDrawColor(200, 200, 200);
  doc.setLineWidth(0.5);
  doc.line(margin, yPos, pageWidth - margin, yPos);
  yPos += 10;

  // --- Key Metrics Section ---
  doc.setFontSize(16);
  doc.setFont('helvetica', 'bold');
  doc.text('Key Metrics', margin, yPos);
  yPos += 10;

  const metrics = validation.metrics || {};
  const statisticalSimilarity = metrics.statistical_similarity || {};

  const keyMetrics = [
    { label: 'Overall Quality Score', value: metrics.quality_score },
    { label: 'Correlation Preservation', value: metrics.correlation_preservation },
    { label: 'Privacy Score', value: metrics.privacy_score },
    { label: 'Statistical Similarity', value: statisticalSimilarity.avg_column_quality },
  ];

  doc.setFontSize(11);
  for (const metric of keyMetrics) {
    doc.setFont('helvetica', 'bold');
    doc.text(`${metric.label}:`, margin + 4, yPos);
    doc.setFont('helvetica', 'normal');
    const displayValue =
      metric.value !== undefined && metric.value !== null
        ? `${(metric.value * 100).toFixed(1)}%`
        : 'N/A';
    doc.text(displayValue, margin + 80, yPos);
    yPos += 7;
  }
  yPos += 6;

  // --- Column-Level Quality Breakdown ---
  const columnMetrics = metrics.column_metrics || {};
  const columnEntries = Object.entries(columnMetrics);

  if (columnEntries.length > 0) {
    addNewPageIfNeeded(30);
    doc.setFontSize(16);
    doc.setFont('helvetica', 'bold');
    doc.text('Column-Level Quality Breakdown', margin, yPos);
    yPos += 10;

    // Table header
    const colNameX = margin;
    const colTypeX = margin + 70;
    const colScoreX = margin + 120;

    doc.setFontSize(10);
    doc.setFont('helvetica', 'bold');
    doc.setFillColor(240, 240, 240);
    doc.rect(margin, yPos - 5, contentWidth, 8, 'F');
    doc.text('Column Name', colNameX + 2, yPos);
    doc.text('Type', colTypeX + 2, yPos);
    doc.text('Quality Score', colScoreX + 2, yPos);
    yPos += 8;

    // Table rows
    doc.setFont('helvetica', 'normal');
    for (const [columnName, columnData] of columnEntries) {
      addNewPageIfNeeded(8);

      const colInfo = columnData as { column_type?: string; quality_score?: number };
      const colType = colInfo.column_type || 'unknown';
      const qualityScore =
        colInfo.quality_score !== undefined && colInfo.quality_score !== null
          ? `${(colInfo.quality_score * 100).toFixed(1)}%`
          : 'N/A';

      // Truncate long column names
      const truncatedName =
        columnName.length > 30 ? columnName.substring(0, 27) + '...' : columnName;

      doc.text(truncatedName, colNameX + 2, yPos);
      doc.text(colType, colTypeX + 2, yPos);
      doc.text(qualityScore, colScoreX + 2, yPos);

      // Light row separator
      doc.setDrawColor(230, 230, 230);
      doc.setLineWidth(0.2);
      doc.line(margin, yPos + 2, pageWidth - margin, yPos + 2);

      yPos += 7;
    }
    yPos += 6;
  }

  // --- Assessment Summary ---
  const assessmentSummary = validation.assessment_summary;
  if (assessmentSummary) {
    addNewPageIfNeeded(30);
    doc.setFontSize(16);
    doc.setFont('helvetica', 'bold');
    doc.text('Assessment Summary', margin, yPos);
    yPos += 10;

    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');

    const wrappedLines = doc.splitTextToSize(assessmentSummary, contentWidth);
    for (const line of wrappedLines) {
      addNewPageIfNeeded(7);
      doc.text(line, margin, yPos);
      yPos += 5;
    }
    yPos += 6;
  }

  // --- Dashboard Screenshot ---
  try {
    const dashboardElement = document.getElementById('results-dashboard');
    if (dashboardElement) {
      const canvas = await html2canvas(dashboardElement, {
        scale: 2,
        useCORS: true,
        logging: false,
        backgroundColor: '#ffffff',
      });

      const imgData = canvas.toDataURL('image/png');
      const imgWidth = contentWidth;
      const imgHeight = (canvas.height / canvas.width) * imgWidth;

      addNewPageIfNeeded(imgHeight + 10);

      doc.setFontSize(16);
      doc.setFont('helvetica', 'bold');
      doc.text('Dashboard Snapshot', margin, yPos);
      yPos += 8;

      // If the image is too tall for the remaining space, start on a new page
      if (yPos + imgHeight > pageHeight - margin) {
        doc.addPage();
        yPos = margin;
      }

      doc.addImage(imgData, 'PNG', margin, yPos, imgWidth, imgHeight);
      yPos += imgHeight + 6;
    }
  } catch {
    // html2canvas capture failed; skip the dashboard image silently
  }

  // --- Footer on last page ---
  doc.setFontSize(8);
  doc.setFont('helvetica', 'italic');
  doc.setTextColor(150, 150, 150);
  doc.text(
    'Generated by DataForge - Synthetic Data Generation Platform',
    pageWidth / 2,
    pageHeight - 10,
    { align: 'center' }
  );

  doc.save(`dataforge_report_${jobId.slice(0, 8)}.pdf`);
}
