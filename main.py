from flask import Flask, render_template_string, request, jsonify, send_file
import requests, io
from PIL import Image

app = Flask(__name__)

# ================= CONFIG =================
SAMBANOVA_API_KEY = "50812343-8406-4a84-be51-af87e847f58a"
SAMBANOVA_URL = "https://api.sambanova.ai/v1/chat/completions"

# In-memory storage for generated images
generated_images = {}

# ================= HTML =================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ChatPilot AI</title>
<style>
:root { --pink: #f8a5c2; --soft-bg: #fdf6f8; }
body, html { height: 100%; margin:0; font-family:'Segoe UI',sans-serif;
background:url('https://share.google/xN8OKM8W6OSdPBFPe') no-repeat center center fixed;
background-size:cover; display:flex; justify-content:center; align-items:center; user-select:none; -webkit-user-select:none;}
.phone { width:360px; height:750px; background:white; border-radius:45px; border:12px solid #222; position:relative; display:flex; flex-direction:column; overflow:hidden; box-shadow:0 30px 60px rgba(0,0,0,0.5);}
.header { padding:20px; text-align:center; border-bottom:1px solid #f0f0f0; font-weight:600; color:#444; background:#fff; font-size:18px;}
.chat-box { flex:1; padding:15px; overflow-y:auto; background:var(--soft-bg); display:flex; flex-direction:column; gap:12px;}
.bot-profile { display:flex; flex-direction:column; margin-bottom:10px; align-items:center;}
.bot-avatar { width:60px; height:60px; border-radius:50%; border:2px solid var(--pink); background:#fff; margin-bottom:5px;}
.status { font-size:11px; color:#888;}
.msg { padding:12px 16px; border-radius:12px; font-size:13.5px; max-width:80%; line-height:1.5; white-space:pre-wrap; word-wrap:break-word; position:relative;}
.bot { background:white; border:1px solid #efefef; align-self:flex-start; color:#444; border-top-left-radius:2px;}
.user { background:var(--pink); color:white; align-self:flex-end; border-top-right-radius:2px;}
.close-btn { position:absolute; top:4px; right:6px; font-size:10px; color:#888; cursor:pointer;}
.floating-actions { position:absolute; right:15px; bottom:120px; display:flex; flex-direction:column; gap:10px; align-items:flex-end;}
.action-chip { background:white; border:none; padding:8px 18px; border-radius:25px; font-size:12px; color:#666; box-shadow:0 4px 12px rgba(0,0,0,0.1); cursor:pointer;}
.input-bar { padding:15px; background:#fff; border-top:1px solid #eee; display:flex; gap:10px; align-items:center;}
input { flex:1; border:none; background:#f5f5f5; padding:12px 18px; border-radius:25px; outline:none;}
.send-btn { background:var(--pink); border:none; color:white; width:38px; height:38px; border-radius:50%; cursor:pointer; display:flex; align-items:center; justify-content:center;}
.typing { display:flex; gap:3px; align-items:center;}
.dot { width:6px; height:6px; background:#888; border-radius:50%; animation:blink 1s infinite;}
.dot:nth-child(2){animation-delay:0.2s;}
.dot:nth-child(3){animation-delay:0.4s;}
@keyframes blink{0%,80%,100%{opacity:0;}40%{opacity:1;}}
.code-block { background:#f4f4f4; border-left:4px solid var(--pink); padding:8px; position:relative;}
.copy-btn { position:absolute; right:8px; top:8px; padding:2px 6px; font-size:11px; background:var(--pink); color:white; border:none; border-radius:4px; cursor:pointer;}
.img-card { width:100%; border-radius:10px; margin-top:10px; border:3px solid white;}
.dl-btn { color:#d63384; font-weight:bold; text-decoration:none; font-size:12px; display:block; margin-top:5px;}
</style>
</head>
<body oncontextmenu="return false;">
<div class="phone">
<div class="header">ChatPilot</div>
<div class="chat-box" id="chat-box">
    <div class="bot-profile">
        <img src="https://cdn-icons-png.flaticon.com/512/4712/4712035.png" class="bot-avatar">
        <span class="status">Online • Hello!</span>
    </div>
    <div class="msg bot">Hello! I am ChatPilot. <br>I can answer queries, generate code, or generate images.</div>
</div>
<div class="floating-actions">
    <button class="action-chip" onclick="quick('Translate')">Translate</button>
    <button class="action-chip" onclick="quick('Summarize')">Summarize</button>
    <button class="action-chip" onclick="quick('Generate code')">Generate Code</button>
    <button class="action-chip" onclick="quick('Generate image')">Generate Image</button>
</div>
<div class="input-bar">
<input type="text" id="user-input" placeholder="Type a message..." onkeypress="if(event.key==='Enter')handleChat()">
<button class="send-btn" onclick="handleChat()">&#10148;</button>
</div>
</div>

<script>
const chatBox=document.getElementById('chat-box');
const inputField=document.getElementById('user-input');

function append(role,content,isCode=false,isImage=false,imgId=""){
    const div=document.createElement('div');
    div.className='msg '+role;

    const closeBtn=document.createElement('span');
    closeBtn.className='close-btn';
    closeBtn.innerText='x';
    closeBtn.onclick=()=>{div.remove();};
    div.appendChild(closeBtn);

    if(isCode){
        const codeDiv=document.createElement('div');
        codeDiv.className='code-block';
        codeDiv.innerHTML=`<pre>${content}</pre><button class="copy-btn" onclick="copyCode(this)">Copy</button>`;
        div.appendChild(codeDiv);
    }else if(isImage){
        div.innerHTML+=`<pre>${content}</pre><img src="/download_image/${imgId}" class="img-card"><a href="/download_image/${imgId}" class="dl-btn" download="AI_Image.png">Download PNG</a>`;
    }else{
        div.innerHTML+=content;
    }
    chatBox.appendChild(div);
    chatBox.scrollTop=chatBox.scrollHeight;
    return div;
}

function copyCode(btn){
    const code=btn.parentElement.querySelector('pre').innerText;
    navigator.clipboard.writeText(code);
    btn.innerText="Copied!";
    setTimeout(()=>{btn.innerText="Copy";},1000);
}

function showTyping(){
    const typingDiv=append('bot','<div class="typing"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>');
    return typingDiv;
}

async function handleChat(type=null){
    const text=type?type:inputField.value.trim();
    if(!text)return;
    if(!type) append('user',text);
    inputField.value='';
    const typingDiv=showTyping();
    try{
        const response=await fetch('/api/chat',{
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({message:text})
        });
        const data=await response.json();
        typingDiv.remove();

        if(text.toLowerCase().includes("generate code")){
            append('bot',data.reply,true);
        }else if(text.toLowerCase().includes("generate image")){
            append('bot',data.reply,false,true,data.image_id);
        }else{
            append('bot',data.reply);
        }
    }catch(e){
        typingDiv.remove();
        append('bot','Server connection error');
    }
}

function quick(cmd){
    handleChat(cmd);
}
</script>
</body>
</html>
"""

# ================= ROUTES =================
@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/chat",methods=["POST"])
def chat():
    user_message = request.json.get("message","").lower()

    # Image generation
    if "generate image" in user_message:
        img = Image.new("RGB",(400,200),color=(255,182,193))
        buf = io.BytesIO()
        img.save(buf,format="PNG")
        buf.seek(0)
        img_id=str(len(generated_images)+1)
        generated_images[img_id]=buf.read()
        return jsonify({"reply":"Here is your AI-generated image:","image_id":img_id})

    # Normal or code AI
    headers={"Authorization":f"Bearer {SAMBANOVA_API_KEY}","Content-Type":"application/json"}
    payload={
        "model":"Meta-Llama-3.1-8B-Instruct",
        "messages":[
            {"role":"system","content":"You are ChatPilot AI. Provide clear answers. If user asks to generate code, provide only code."},
            {"role":"user","content":user_message}
        ],
        "temperature":0.2,"top_p":0.9
    }
    try:
        r=requests.post(SAMBANOVA_URL,json=payload,headers=headers,timeout=60)
        if r.status_code!=200:return jsonify({"reply":f"SambaNova Error {r.status_code}"})
        data=r.json()
        reply=data["choices"][0]["message"]["content"] if "choices" in data else "No reply from AI"
        return jsonify({"reply":reply})
    except Exception as e:
        return jsonify({"reply":f"Server error: {str(e)}"})

@app.route("/download_image/<img_id>")
def download_image(img_id):
    img_data = generated_images.get(img_id)
    if img_data:
        return send_file(io.BytesIO(img_data), mimetype="image/png", download_name="AI_Image.png")
    return "Image not found",404

# ================= RUN =================
if __name__=="__main__":
    app.run(debug=True,port=5000)
