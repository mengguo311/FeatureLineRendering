import Foundation
import AppKit
import PDFKit
let root="/Users/menakuniay/.hermes/research-deliveries/line_kernel_relaxed_guards_v10_20261103"
let doc=PDFDocument(url: URL(fileURLWithPath:root+"/REPORT_ZH.pdf"))!
let indexes=[0,doc.pageCount/2,doc.pageCount-1]
var records:[[String:Any]]=[]
for i in indexes {
 let p=doc.page(at:i)!
 let bounds=p.bounds(for:.mediaBox)
 let scale:CGFloat=1.5
 let rep=NSBitmapImageRep(bitmapDataPlanes:nil,pixelsWide:Int(bounds.width*scale),pixelsHigh:Int(bounds.height*scale),bitsPerSample:8,samplesPerPixel:4,hasAlpha:true,isPlanar:false,colorSpaceName:.deviceRGB,bytesPerRow:0,bitsPerPixel:0)!
 let ctx=NSGraphicsContext(bitmapImageRep:rep)!
 NSGraphicsContext.saveGraphicsState();NSGraphicsContext.current=ctx
 NSColor.white.setFill();NSRect(x:0,y:0,width:bounds.width*scale,height:bounds.height*scale).fill()
 ctx.cgContext.scaleBy(x:scale,y:scale);p.draw(with:.mediaBox,to:ctx.cgContext)
 NSGraphicsContext.restoreGraphicsState()
 let name="pdf_check_page_\(i+1).png"
 try rep.representation(using:.png,properties:[:])!.write(to:URL(fileURLWithPath:root+"/"+name))
 records.append(["page":i+1,"image":name,"text_characters":p.string?.count ?? 0,"text_excerpt":String((p.string ?? "").prefix(160))])
}
let obj:[String:Any]=["pages":doc.pageCount,"checked":records,"renderer":"macOS PDFKit","all_page_text_characters":(0..<doc.pageCount).map{doc.page(at:$0)?.string?.count ?? 0}]
let bytes=try JSONSerialization.data(withJSONObject:obj,options:[.prettyPrinted,.sortedKeys])
try bytes.write(to:URL(fileURLWithPath:root+"/PDF_RENDER_CHECK.json"));print(String(data:bytes,encoding:.utf8)!)
