import { toast } from "sonner";
import type { AuditResultResponse } from "@/lib/api";

export function exportAuditAsJson(result: AuditResultResponse, filename = "audit-report.json") {
    try {
        const dataStr = JSON.stringify(result, null, 2);
        const blob = new Blob([dataStr], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        toast.success("JSON report exported successfully.");
    } catch {
        toast.error("Failed to export JSON report.");
    }
}

export async function exportAuditAsPdf(result: AuditResultResponse, filename = "audit-report.pdf") {
    try {
        // Loaded on demand: jsPDF is ~300KB and only needed when exporting.
        const { default: jsPDF } = await import("jspdf");
        const doc = new jsPDF();
        const pageWidth = doc.internal.pageSize.getWidth();
        let yPos = 20;

        doc.setFontSize(22);
        doc.text("Audit Report", 14, yPos);
        yPos += 10;

        doc.setFontSize(12);
        doc.text(`Total Files: ${result.total_files}`, 14, yPos);
        yPos += 8;
        doc.text(`Date: ${new Date().toLocaleDateString()}`, 14, yPos);
        yPos += 15;

        result.results.forEach((file) => {
            if (yPos > doc.internal.pageSize.getHeight() - 40) {
                doc.addPage();
                yPos = 20;
            }

            doc.setFontSize(14);
            doc.text(`File: ${file.file_path}`, 14, yPos);
            yPos += 8;

            if (file.error) {
                doc.setFontSize(10);
                doc.text(`Error: ${file.error}`, 14, yPos);
                yPos += 12;
            } else {
                doc.setFontSize(10);
                const lines = doc.splitTextToSize(
                    file.final_report || "No report generated.",
                    pageWidth - 28
                );
                doc.text(lines, 14, yPos);
                yPos += lines.length * 5 + 10;
            }
        });

        doc.save(filename);
        toast.success("PDF report exported successfully.");
    } catch (e) {
        console.error(e);
        toast.error("Failed to generate PDF report.");
    }
}
