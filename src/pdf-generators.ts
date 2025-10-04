import jsPDF from 'jspdf';
import { ResumeData } from './types';

const FONT_SIZES = {
    header: 24,
    title: 14,
    subtitle: 11,
    body: 10,
    small: 9,
};

const MARGIN = 40;

const addWrappedText = (doc: jsPDF, text: string, x: number, y: number, options: { width: number, font?: string, size?: number, color?: string | number | [number, number, number] }) => {
    if (options.font) doc.setFont(options.font);
    if (options.size) doc.setFontSize(options.size);
    if (options.color) {
        if (Array.isArray(options.color)) doc.setTextColor(...options.color);
        else doc.setTextColor(options.color as any);
    }

    const lines = doc.splitTextToSize(text, options.width);
    doc.text(lines, x, y);
    return lines.length * (options.size || FONT_SIZES.body) * 0.8;
};

export const generateClassicPDF = (doc: jsPDF, data: ResumeData) => {
    const { personalInfo, summary, experience, education, skills, accentColor } = data;
    const pageWidth = doc.internal.pageSize.getWidth();
    const contentWidth = pageWidth - MARGIN * 2;
    let y = MARGIN;

    // --- Header ---
    doc.setFont('times', 'bold').setFontSize(FONT_SIZES.header).setTextColor(accentColor);
    doc.text(personalInfo.fullName, pageWidth / 2, y, { align: 'center' });
    y += 25;
    
    doc.setFont('times', 'normal').setFontSize(FONT_SIZES.body).setTextColor(80, 80, 80);
    const contactInfo = [personalInfo.email, personalInfo.phoneNumber, personalInfo.address].filter(Boolean).join(' | ');
    doc.text(contactInfo, pageWidth / 2, y, { align: 'center' });
    y += 20;
    
    doc.setDrawColor(accentColor).setLineWidth(1).line(MARGIN, y, pageWidth - MARGIN, y);
    y += 30;

    // --- Summary ---
    if (summary) {
        doc.setFont('times', 'bold').setFontSize(FONT_SIZES.title).setTextColor(50, 50, 50);
        doc.text('Professional Summary', MARGIN, y);
        y += 20;
        const height = addWrappedText(doc, summary, MARGIN, y, { width: contentWidth, font: 'times', size: FONT_SIZES.body, color: [80, 80, 80] });
        y += height + 20;
    }

    // --- Experience ---
    if (experience.length > 0) {
        doc.setFont('times', 'bold').setFontSize(FONT_SIZES.title).setTextColor(50, 50, 50);
        doc.text('Work Experience', MARGIN, y);
        y += 20;
        experience.forEach(exp => {
            if (y > doc.internal.pageSize.getHeight() - MARGIN * 2) {
                doc.addPage();
                y = MARGIN;
            }
            doc.setFont('times', 'bold').setFontSize(FONT_SIZES.subtitle);
            doc.text(exp.role, MARGIN, y);
            const dateText = `${exp.startDate} - ${exp.endDate || 'Present'}`;
            doc.text(dateText, pageWidth - MARGIN, y, { align: 'right' });
            y += 14;

            doc.setFont('times', 'italic').setFontSize(FONT_SIZES.body).setTextColor(100, 100, 100);
            doc.text(exp.company, MARGIN, y);
            y += 18;

            const descLines = exp.description.split('\n').filter(l => l.trim());
            descLines.forEach((line) => {
                const height = addWrappedText(doc, line.replace(/•\s*/, ''), MARGIN + 15, y, { width: contentWidth - 15, font: 'times', size: FONT_SIZES.body, color: [80, 80, 80] });
                doc.text('•', MARGIN, y);
                y += height + 2;
            });
            y += 15;
        });
    }

    // --- Education ---
    if (education.length > 0) {
        if (y > doc.internal.pageSize.getHeight() - MARGIN * 2) {
            doc.addPage();
            y = MARGIN;
        }
        doc.setFont('times', 'bold').setFontSize(FONT_SIZES.title).setTextColor(50, 50, 50);
        doc.text('Education', MARGIN, y);
        y += 20;
        education.forEach(edu => {
            doc.setFont('times', 'bold').setFontSize(FONT_SIZES.subtitle);
            doc.text(edu.degree, MARGIN, y);
            const dateText = `${edu.startDate} - ${edu.endDate}`;
            doc.text(dateText, pageWidth - MARGIN, y, { align: 'right' });
            y += 14;

            doc.setFont('times', 'italic').setFontSize(FONT_SIZES.body).setTextColor(100, 100, 100);
            doc.text(edu.institution, MARGIN, y);
            y += 20;
        });
    }

     // --- Skills ---
     if (skills.length > 0) {
        if (y > doc.internal.pageSize.getHeight() - MARGIN) {
            doc.addPage();
            y = MARGIN;
        }
        doc.setFont('times', 'bold').setFontSize(FONT_SIZES.title).setTextColor(50, 50, 50);
        doc.text('Skills', MARGIN, y);
        y += 20;
        addWrappedText(doc, skills.join(' · '), MARGIN, y, { width: contentWidth, font: 'times', size: FONT_SIZES.body, color: [80, 80, 80]});
    }
}

export const generateModernPDF = (doc: jsPDF, data: ResumeData) => {
    const { personalInfo, summary, experience, education, skills, accentColor } = data;
    const pageWidth = doc.internal.pageSize.getWidth();
    
    const leftColWidth = 150;
    const rightColX = MARGIN + leftColWidth + 20;
    const rightColWidth = pageWidth - rightColX - MARGIN;
    let leftY = MARGIN;
    let rightY = MARGIN;

    // --- LEFT COLUMN ---
    doc.setFont('helvetica', 'bold').setFontSize(18).setTextColor(50, 50, 50);
    leftY += addWrappedText(doc, personalInfo.fullName, MARGIN, leftY, { width: leftColWidth, size: 18, color: '#374151' });
    leftY += 20;

    doc.setFont('helvetica', 'normal').setFontSize(FONT_SIZES.small).setTextColor(80,80,80);
    if(personalInfo.email) {
        leftY += addWrappedText(doc, personalInfo.email, MARGIN, leftY, { width: leftColWidth, size: FONT_SIZES.small });
        leftY += 5;
    }
    if(personalInfo.phoneNumber) {
        leftY += addWrappedText(doc, personalInfo.phoneNumber, MARGIN, leftY, { width: leftColWidth, size: FONT_SIZES.small });
        leftY += 5;
    }
    if(personalInfo.address) {
        leftY += addWrappedText(doc, personalInfo.address, MARGIN, leftY, { width: leftColWidth, size: FONT_SIZES.small });
    }
    leftY += 30;

    if (education.length > 0) {
        doc.setFont('helvetica', 'bold').setFontSize(FONT_SIZES.body).setTextColor(accentColor);
        doc.text('EDUCATION', MARGIN, leftY);
        leftY += 15;
        education.forEach(edu => {
            doc.setFont('helvetica', 'bold').setFontSize(FONT_SIZES.small).setTextColor(50, 50, 50);
            leftY += addWrappedText(doc, edu.degree, MARGIN, leftY, { width: leftColWidth, size: FONT_SIZES.small });
            
            doc.setFont('helvetica', 'normal').setTextColor(100, 100, 100);
            leftY += addWrappedText(doc, edu.institution, MARGIN, leftY, { width: leftColWidth, size: FONT_SIZES.small });
            leftY += addWrappedText(doc, `${edu.startDate} - ${edu.endDate}`, MARGIN, leftY, { width: leftColWidth, size: FONT_SIZES.small });
            leftY += 15;
        });
    }

    if (skills.length > 0) {
        doc.setFont('helvetica', 'bold').setFontSize(FONT_SIZES.body).setTextColor(accentColor);
        doc.text('SKILLS', MARGIN, leftY);
        leftY += 15;
        doc.setFont('helvetica', 'normal').setFontSize(FONT_SIZES.small).setTextColor(80, 80, 80);
        skills.forEach(skill => {
            leftY += addWrappedText(doc, `• ${skill}`, MARGIN, leftY, { width: leftColWidth, size: FONT_SIZES.small });
            leftY += 2;
        });
    }


    // --- RIGHT COLUMN ---
    if (summary) {
        doc.setFont('helvetica', 'bold').setFontSize(FONT_SIZES.body).setTextColor(accentColor);
        doc.text('SUMMARY', rightColX, rightY);
        rightY += 15;
        const height = addWrappedText(doc, summary, rightColX, rightY, { width: rightColWidth, font: 'helvetica', size: FONT_SIZES.small, color: [80, 80, 80] });
        rightY += height + 20;
    }

    if (experience.length > 0) {
        doc.setFont('helvetica', 'bold').setFontSize(FONT_SIZES.body).setTextColor(accentColor);
        doc.text('EXPERIENCE', rightColX, rightY);
        rightY += 15;
        experience.forEach(exp => {
             if (rightY > doc.internal.pageSize.getHeight() - MARGIN * 2) {
                doc.addPage();
                rightY = MARGIN;
            }
            doc.setFont('helvetica', 'bold').setFontSize(FONT_SIZES.subtitle).setTextColor(50, 50, 50);
            rightY += addWrappedText(doc, exp.role, rightColX, rightY, { width: rightColWidth, size: FONT_SIZES.subtitle });

            doc.setFont('helvetica', 'normal').setFontSize(FONT_SIZES.small).setTextColor(100, 100, 100);
            const companyDate = `${exp.company} | ${exp.startDate} - ${exp.endDate || 'Present'}`;
            rightY += addWrappedText(doc, companyDate, rightColX, rightY, { width: rightColWidth, size: FONT_SIZES.small});
            rightY += 10;

            const descLines = exp.description.split('\n').filter(l => l.trim());
            descLines.forEach((line) => {
                const height = addWrappedText(doc, line.replace(/•\s*/, ''), rightColX + 10, rightY, { width: rightColWidth - 10, font: 'helvetica', size: FONT_SIZES.small, color: [80, 80, 80] });
                doc.text('•', rightColX, rightY);
                rightY += height + 2;
            });
            rightY += 15;
        });
    }
};