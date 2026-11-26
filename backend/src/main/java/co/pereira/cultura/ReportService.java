package co.pereira.cultura;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.math.BigDecimal;
import java.util.*;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import com.lowagie.text.Document;
import com.lowagie.text.Element;
import com.lowagie.text.FontFactory;
import com.lowagie.text.Paragraph;
import com.lowagie.text.Phrase;
import com.lowagie.text.PageSize;
import com.lowagie.text.pdf.PdfWriter;
import com.lowagie.text.pdf.PdfPTable;
import com.lowagie.text.pdf.PdfPCell;
import java.awt.Color;
import org.springframework.http.*;
import org.springframework.stereotype.Service;

@Service
public class ReportService {
    private final RecordsService records;private final AuthService auth;
    private static final Set<String> META=Set.of("created_at","created_by","updated_at","updated_by");
    public ReportService(RecordsService records,AuthService auth){this.records=records;this.auth=auth;}
    private List<String> columns(RecordsService.Resource r){List<String> c=new ArrayList<>();c.add("id");c.addAll(r.fields());if(r.table().equals("cajas_menores")){c.add("ciclo");c.add("estado");}if(Set.of("gastos_caja_menor","reintegros_caja_menor").contains(r.table()))c.add("ciclo");if(r.table().equals("convenios"))c.addAll(List.of("estado","fecha_envio_contaduria","fecha_liquidacion","fecha_envio_liquidacion"));return c;}
    ResponseEntity<byte[]> export(String entity,String format,AuthService.User u) throws IOException {RecordsService.Resource r=RecordsService.byReport(entity);List<Map<String,Object>> data=records.reportRows(r,u);List<String> cols=columns(r);byte[] bytes;String media;switch(format){case "xlsx"->{bytes=xlsx(cols,data);media="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";}case "pdf"->{bytes=pdf(entity,cols,data);media="application/pdf";}default->throw ApiFailure.bad("Formato permitido: xlsx o pdf");}auth.audit(u.username(),"EXPORTAR",r.table(),null,format);return ResponseEntity.ok().header(HttpHeaders.CONTENT_DISPOSITION,ContentDisposition.attachment().filename(entity+"."+format).build().toString()).contentType(MediaType.parseMediaType(media)).body(bytes);}
    private static String value(Object v){return v==null?"":v instanceof BigDecimal n?n.toPlainString():v.toString();}
    private byte[] xlsx(List<String> cols,List<Map<String,Object>> data) throws IOException {try(XSSFWorkbook wb=new XSSFWorkbook();ByteArrayOutputStream out=new ByteArrayOutputStream()){Sheet sh=wb.createSheet("Reporte");CellStyle header=wb.createCellStyle();org.apache.poi.ss.usermodel.Font font=wb.createFont();font.setBold(true);font.setColor(IndexedColors.WHITE.getIndex());header.setFont(font);header.setFillForegroundColor(IndexedColors.DARK_TEAL.getIndex());header.setFillPattern(FillPatternType.SOLID_FOREGROUND);CellStyle wrapped=wb.createCellStyle();wrapped.setWrapText(true);wrapped.setVerticalAlignment(VerticalAlignment.TOP);Row hr=sh.createRow(0);for(int i=0;i<cols.size();i++){Cell c=hr.createCell(i);c.setCellValue(cols.get(i));c.setCellStyle(header);sh.setColumnWidth(i,Math.min(45,Math.max(16,cols.get(i).length()+4))*256);}int row=1;for(Map<String,Object> d:data){Row rr=sh.createRow(row++);for(int i=0;i<cols.size();i++){Cell c=rr.createCell(i);Object v=d.get(cols.get(i));if(v instanceof Number n)c.setCellValue(n.doubleValue());else c.setCellValue(value(v));c.setCellStyle(wrapped);}}sh.createFreezePane(0,1);sh.setAutoFilter(new org.apache.poi.ss.util.CellRangeAddress(0,Math.max(0,data.size()),0,cols.size()-1));wb.write(out);return out.toByteArray();}}
    private byte[] pdf(String entity,List<String> cols,List<Map<String,Object>> data) throws IOException {try(ByteArrayOutputStream out=new ByteArrayOutputStream()){Document doc=new Document(PageSize.A4,38,38,42,42);try{PdfWriter.getInstance(doc,out);doc.open();Paragraph title=new Paragraph("Reporte administrativo: "+entity,FontFactory.getFont(FontFactory.HELVETICA_BOLD,17));title.setSpacingAfter(8);doc.add(title);doc.add(new Paragraph("Registros: "+data.size(),FontFactory.getFont(FontFactory.HELVETICA,10)));if(data.isEmpty())doc.add(new Paragraph("No hay registros para este reporte."));for(Map<String,Object> r:data){Paragraph heading=new Paragraph("Registro "+value(r.get("id")),FontFactory.getFont(FontFactory.HELVETICA_BOLD,12));heading.setSpacingBefore(12);heading.setSpacingAfter(5);doc.add(heading);PdfPTable table=new PdfPTable(new float[]{1.2f,3f});table.setWidthPercentage(100);table.setSplitRows(true);table.setSplitLate(false);for(String col:cols){PdfPCell left=new PdfPCell(new Phrase(col.replace('_',' '),FontFactory.getFont(FontFactory.HELVETICA_BOLD,9)));left.setBackgroundColor(new Color(232,240,242));left.setPadding(5);left.setVerticalAlignment(Element.ALIGN_TOP);table.addCell(left);PdfPCell right=new PdfPCell(new Phrase(value(r.get(col)),FontFactory.getFont(FontFactory.HELVETICA,9)));right.setPadding(5);right.setVerticalAlignment(Element.ALIGN_TOP);table.addCell(right);}doc.add(table);}}catch(Exception e){throw new IOException("No se pudo generar el reporte PDF",e);}finally{if(doc.isOpen())doc.close();}return out.toByteArray();}}
}
