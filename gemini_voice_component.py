"""Streamlit Components V2 mic control for the local Gemini Live websocket bridge."""
import streamlit as st

JS = r'''
export default function({parentElement, setTriggerValue}) {
  const button = parentElement.querySelector("#voice-toggle");
  const label = parentElement.querySelector("#voice-status");
  // Keep media and websocket objects across Streamlit's rerender cycle.
  const state = globalThis.__zeilGeminiVoice ||= {
    ws:null, stream:null, context:null, source:null, processor:null,
    started:false, status:"Microphone off", emit:null, render:null
  };
  state.emit = (page) => setTriggerValue("command", page + ":" + Date.now());
  state.render = () => {
    label.textContent = state.status;
    button.textContent = state.started ? "Stop Gemini Live" : "Enable Gemini Live";
  };
  const update = (s) => { state.status=s; state.render?.(); };
  state.render();

  function scrollDashboard(direction, amount) {
    // V2 components execute in the Streamlit document, not an iframe.
    // The main Streamlit scroll container is used when present.
    const candidates = [
      document.querySelector('[data-testid="stMain"]'),
      document.querySelector('[data-testid="stAppViewContainer"]'),
      document.scrollingElement,
    ].filter(Boolean);
    const container = candidates.find(el => el.scrollHeight > el.clientHeight + 20)
      || document.scrollingElement;
    const distance = Math.min(1200, Math.max(100, Number(amount) || 500));
    if (!container) { update("Scroll container not found"); return; }
    if (direction === "top" || direction === "bottom") {
      container.scrollTo({top: direction === "top" ? 0 : container.scrollHeight, behavior:"smooth"});
    } else {
      container.scrollBy({top: direction === "up" ? -distance : distance, behavior:"smooth"});
    }
    update("Scrolling " + direction);
  }

  function downsample(buffer, sourceRate) {
    const ratio=sourceRate/16000;
    const data=new Int16Array(Math.floor(buffer.length/ratio));
    for(let i=0;i<data.length;i++) {
      let v=buffer[Math.floor(i*ratio)]||0;
      v=Math.max(-1,Math.min(1,v));
      data[i]=v<0?v*32768:v*32767;
    }
    return data.buffer;
  }
  async function stop() {
    state.started=false;
    try {state.processor?.disconnect();state.source?.disconnect();} catch (_) {}
    state.stream?.getTracks().forEach(t=>t.stop());
    await state.context?.close().catch(()=>{});
    if(state.ws?.readyState===WebSocket.OPEN)state.ws.close();
    state.ws=null;state.context=null;state.stream=null;
    update("Microphone off");
  }
  async function start() {
    button.disabled=true;
    update("Connecting to Gemini...");
    try {
      const ws=new WebSocket("ws://127.0.0.1:8766");
      state.ws=ws;
      ws.onmessage=(event)=>{
        const msg=JSON.parse(event.data);
        if(msg.type==="ready")update("Listening via Gemini Live");
        if(msg.type==="error")update("Gemini error: "+msg.message);
        if(msg.type==="navigate") {update("Navigating to "+msg.page);state.emit?.(msg.page);}
        if(msg.type==="scroll") scrollDashboard(msg.direction, msg.amount);
        if(msg.type==="investigate") {
          update("Starting AI investigation...");
          state.emit?.("investigate_now");
        }
        if(msg.type==="dataset") {
          update("Loading CSV: " + msg.dataset);
          state.emit?.("dataset|" + msg.dataset);
        }
      };
      ws.onclose=()=>{if(state.started)update("Connection closed. Restart microphone.");};
      await new Promise((resolve,reject)=>{
        ws.addEventListener("open",resolve,{once:true});
        ws.addEventListener("error",()=>reject(new Error("Bridge unavailable")),{once:true});
      });
      state.stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true}});
      state.context=new AudioContext();
      state.source=state.context.createMediaStreamSource(state.stream);
      state.processor=state.context.createScriptProcessor(2048,1,1);
      state.processor.onaudioprocess=(event)=>{
        if(state.ws?.readyState===WebSocket.OPEN)
          state.ws.send(downsample(event.inputBuffer.getChannelData(0),state.context.sampleRate));
        event.outputBuffer.getChannelData(0).fill(0);
      };
      state.source.connect(state.processor);
      state.processor.connect(state.context.destination);
      state.started=true;
      update("Listening via Gemini Live");
    } catch(e) {await stop();update("Error: "+e.message);}
    finally {button.disabled=false;}
  }
  button.onclick=()=>state.started?stop():start();
  // Do not close mic during ordinary Streamlit reruns.
  return ()=>{state.render=null;};
}
'''

CSS = """
#voice-panel { background:#EAF1E7; border:1px solid #CEDDCB;
  border-radius:15px; padding:16px; color:#264C38; display:flex;
  align-items:center; gap:16px; }
#voice-toggle { background:#356B51; border:0; border-radius:10px;
  padding:12px 18px; color:white; font-weight:650; cursor:pointer; }
#voice-status {font-size:15px; color:#426451; }
"""

component = st.components.v2.component(
    name="gemini_live_voice_nav",
    html='<div id="voice-panel"><button id="voice-toggle">Enable Gemini Live</button><span id="voice-status">Microphone off</span></div>',
    css=CSS, js=JS,
)

def voice_navigation():
    return component(key="gemini_voice", on_command_change=lambda: None)
