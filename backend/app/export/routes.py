import io
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.database import get_db
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

router = APIRouter(prefix="/rooms/{room_id}/export", tags=["export"])

@router.get("/markdown")
async def export_markdown(room_id: str):
    """Export room transcript and decisions as Markdown"""
    db = get_db()
    
    room = await db["rooms"].find_one({"_id": room_id})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
        
    messages_cursor = db["messages"].find({"room_id": room_id}).sort("created_at", 1)
    messages = await messages_cursor.to_list(length=1000)
    
    decisions_cursor = db["agent_outputs"].find({"room_id": room_id, "status": "finalized"})
    decisions = await decisions_cursor.to_list(length=100)
    
    # Compile Markdown Document
    md = f"""# ForgeRoom Document Review: {room['name']}

**Room ID**: {room_id}
**Exported At**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
**Contract Clause**:
{room.get('contract_text', 'No contract clause uploaded.')}

---

## Finalized Decisions Matrix
"""
    if decisions:
        for dec in decisions:
            md += f"### ✓ {dec['title']}\n{dec['content']}\n\n"
    else:
        md += "_No decisions marked as finalized yet._\n\n"
        
    md += "--- \n\n## Session Discussion Log\n"
    for msg in messages:
        timestamp = msg["created_at"].strftime('%H:%M:%S')
        if msg["message_type"] == "user":
            md += f"**@{msg['username']}** ({timestamp}):\n{msg['content']}\n\n"
        else:
            md += f"🤖 **{msg['username']}** ({timestamp}):\n{msg['content']}\n\n"
            
    return StreamingResponse(
        iter([md]),
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=forgeroom_export_{room_id[:8]}.md"}
    )

@router.get("/pdf")
async def export_pdf(room_id: str):
    """Export room transcript and decisions as a printable PDF using reportlab"""
    db = get_db()
    
    room = await db["rooms"].find_one({"_id": room_id})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
        
    messages_cursor = db["messages"].find({"room_id": room_id}).sort("created_at", 1)
    messages = await messages_cursor.to_list(length=1000)
    
    decisions_cursor = db["agent_outputs"].find({"room_id": room_id, "status": "finalized"})
    decisions = await decisions_cursor.to_list(length=100)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = styles['Heading1']
    title_style.textColor = "#1a237e"
    h2_style = styles['Heading2']
    h2_style.textColor = "#00e5ff"
    normal_style = styles['Normal']
    
    story = []
    
    # Header Information
    story.append(Paragraph(f"<b>ForgeRoom Transcript: {room['name']}</b>", title_style))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"<b>Room ID:</b> {room_id}", normal_style))
    story.append(Paragraph(f"<b>Export Date:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
    story.append(Spacer(1, 15))
    
    # Contract text
    story.append(Paragraph("<b>Uploaded Clause Context:</b>", styles['Heading3']))
    contract_txt = room.get('contract_text', 'None uploaded.')
    story.append(Paragraph(contract_txt.replace("\n", "<br/>"), normal_style))
    story.append(Spacer(1, 20))
    
    # Decisions Section
    story.append(Paragraph("<b>Finalized Decisions Matrix</b>", h2_style))
    story.append(Spacer(1, 8))
    if decisions:
        for dec in decisions:
            story.append(Paragraph(f"<b>✓ {dec['title']}</b>", styles['Heading4']))
            story.append(Paragraph(dec['content'].replace("\n", "<br/>"), normal_style))
            story.append(Spacer(1, 8))
    else:
        story.append(Paragraph("No decisions marked as finalized yet.", normal_style))
    story.append(Spacer(1, 20))
    
    # Messages list
    story.append(Paragraph("<b>Session Discussion Log</b>", h2_style))
    story.append(Spacer(1, 10))
    
    for msg in messages:
        timestamp = msg["created_at"].strftime('%H:%M:%S')
        speaker = msg['username'] if msg['message_type'] == 'user' else '🤖 ForgeBot'
        story.append(Paragraph(f"<b>{speaker}</b> ({timestamp}):", styles['Normal']))
        story.append(Paragraph(msg['content'].replace("\n", "<br/>"), normal_style))
        story.append(Spacer(1, 8))
        
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=forgeroom_export_{room_id[:8]}.pdf"}
    )

@router.get("/copy")
async def export_copy_text(room_id: str):
    """Return JSON representation of Markdown text to copy to clipboard"""
    db = get_db()
    
    room = await db["rooms"].find_one({"_id": room_id})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
        
    messages_cursor = db["messages"].find({"room_id": room_id}).sort("created_at", 1)
    messages = await messages_cursor.to_list(length=1000)
    
    md = f"# ForgeRoom Session: {room['name']}\n\n"
    for msg in messages:
        timestamp = msg["created_at"].strftime('%H:%M:%S')
        speaker = f"@{msg['username']}" if msg['message_type'] == 'user' else "🤖 ForgeBot"
        md += f"**{speaker}** ({timestamp}):\n{msg['content']}\n\n"
        
    return {"markdown": md, "copy_ready": True}
