/**
 * PDF Generators for Resume Templates
 * 
 * This module provides utilities for generating PDF resumes.
 * Currently uses browser print API via window.print() which is called from ResumePreview.tsx
 * 
 * Future enhancements could include:
 * - Server-side PDF generation with libraries like PDFKit or Puppeteer
 * - Client-side PDF generation with jsPDF
 * - Custom styling and layouts
 */

export interface PDFGeneratorOptions {
  template: 'classic' | 'modern';
  filename?: string;
}

/**
 * Trigger browser print dialog for PDF generation
 * This is a lightweight solution that works well for most cases
 */
export const generatePDFViaPrint = (options: PDFGeneratorOptions): void => {
  const { filename } = options;
  
  if (filename) {
    const originalTitle = document.title;
    document.title = filename;
    window.print();
    document.title = originalTitle;
  } else {
    window.print();
  }
};

/**
 * Future: Client-side PDF generation placeholder
 * Could be implemented with jsPDF library
 */
export const generatePDFClient = async (
  element: HTMLElement, 
  options: PDFGeneratorOptions
): Promise<void> => {
  // Placeholder for future implementation
  console.log('Client-side PDF generation not yet implemented');
  console.log('Using browser print as fallback');
  generatePDFViaPrint(options);
};

/**
 * Export all PDF utilities
 */
export const PDFGenerators = {
  print: generatePDFViaPrint,
  client: generatePDFClient,
};

export default PDFGenerators;
