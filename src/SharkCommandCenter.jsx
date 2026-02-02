import React, { useState, useEffect, useRef, useCallback } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

// ─── SHARK LOGO COMPONENT ───────────────────────────────────────────────────
const SharkLogo = ({ size = 100, emergencyMode = false, intensity = 1 }) => (
  <svg width={size} height={size} viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
        <feMerge>
          <feMergeNode in="coloredBlur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
    </defs>
    <ellipse cx="100" cy="115" rx="82" ry="78" fill="rgba(0,0,0,0.4)" />
    <path 
      d="M100 38C55 38 18 75 18 120C18 165 55 202 100 202C145 202 182 165 182 120C182 75 145 38 100 38Z" 
      fill={emergencyMode ? "#dc2626" : "#ef4444"} 
      stroke={emergencyMode ? "#f87171" : "#000"} 
      strokeWidth="4"
      filter={intensity > 1.5 ? "url(#glow)" : ""}
      style={{ transition: 'all 0.3s ease' }}
    />
    <path d="M38 105C38 85 65 70 100 70C135 70 162 85 162 105C162 115 135 125 100 125C65 125 38 115 38 105Z" fill="#2563eb" />
    <ellipse cx="100" cy="145" rx="65" ry="45" fill="#ffffff" stroke="#000" strokeWidth="3" />
    <rect x="55" y="135" width="90" height="25" rx="8" fill="#1a1a1a" />
    <path d="M55 135 L62 148 L70 135 L78 148 L86 135 L94 148 L102 135 L110 148 L118 135 L126 148 L134 135 L142 148 L145 135" stroke="white" strokeWidth="2.5" fill="white" />
    <path d="M58 160 L65 147 L73 160 L81 147 L89 160 L97 147 L105 160 L113 147 L121 160 L129 147 L137 160 L142 147" stroke="white" strokeWidth="2.5" fill="white" />
    <circle cx="75" cy="100" r="7" fill={emergencyMode ? "#f87171" : "black"} />
    <circle cx="125" cy="100" r="7" fill={emergencyMode ? "#f87171" : "black"} />
    <path d="M100 15 L85 50 L115 50 Z" fill={emergencyMode ? "#dc2626" : "#ef4444"} stroke="#000" strokeWidth="3" />
    <path d="M20 110 L5 130 L25 135 Z" fill={emergencyMode ? "#dc2626" : "#ef4444"} stroke="#000" strokeWidth="3" />
    <path d="M180 110 L195 130 L175 135 Z" fill={emergencyMode ? "#dc2626" : "#ef4444"} stroke="#000" strokeWidth="3" />
  </svg>
);

// ─── STYLES & ANIMATIONS ───────────────────────────────────────────────────
const CSS = `
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;600;800&display=swap');
  
  @keyframes sharkProwl { 
    0%, 100% { transform: translateY(0px) translateX(0px) rotate(-2deg); }
    33% { transform: translateY(-10px) translateX(5px) rotate(2deg); }
    66% { transform: translateY(5px) translateX(-5px) rotate(-1deg); }
  }
  @keyframes sonarSweep {
    0% { transform: scale(0.1); opacity: 0; }
    10% { opacity: 0.4; }
    100% { transform: scale(3.5); opacity: 0; }
  }
  @keyframes emergencyPulse {
    0%, 100% { box-shadow: inset 0 0 50px rgba(220,38,38,0.2); }
    50% { box-shadow: inset 0 0 100px rgba(220,38,38,0.6); }
  }
  @keyframes thinkingPulse {
    0%, 100% { opacity: 0.3; }
    50% { opacity: 1; }
  }
  @keyframes slideIn {
    from { opacity: 0; transform: translateY(-10px); }
    to { opacity: 1; transform: translateY(0); }
  }
  @keyframes tokenBurn {
    0% { transform: translateY(0); opacity: 1; }
    100% { transform: translateY(-20px); opacity: 0; }
  }

  .dw-panel { 
    backdrop-filter: blur(20px); 
    border-radius: 12px; 
    border: 1px solid rgba(100,180,255,0.1); 
    background: rgba(4, 12, 24, 0.7); 
    transition: all 0.3s ease;
  }
  .dw-panel:hover {
    border-color: rgba(100,180,255,0.2);
    background: rgba(4, 12, 24, 0.8);
  }
  .ocean-bg {
    position: fixed; inset: 0; z-index: -1;
    background: radial-gradient(circle at 50% 50%, #0f172a 0%, #020617 100%);
  }
  .sonar-ring {
    position: absolute; top: 50%; left: 50%; width: 600px; height: 600px;
    margin-left: -300px; margin-top: -300px;
    border: 1px solid rgba(34, 197, 94, 0.15); border-radius: 50%;
    animation: sonarSweep 5s linear infinite; pointer-events: none;
  }
  .tool-execution {
    animation: slideIn 0.3s ease-out;
  }
  .thinking-stream {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #64748b;
    line-height: 1.5;
  }
  .token-flash {
    position: absolute;
    color: #fbbf24;
    font-size: 10px;
    animation: tokenBurn 1s ease-out forwards;
    pointer-events: none;
  }
`;

// ─── MOCK WEBSOCKET HOOK (Replace with real socket.io) ─────────────────────
const useAgentStream = () => {
  const [stream, setStream] = useState([]);
  const [thinking, setThinking] = useState("");
  const [currentTool, setCurrentTool] = useState(null);
  
  useEffect(() => {
    // Simulate DeepSeek streaming
    const interval = setInterval(() => {
      if (Math.random() > 0.7) {
        setThinking(prev => prev + " " + ["Analyzing...", "Checking context...", "Optimizing...", "Reasoning..."][Math.floor(Math.random() * 4)]);
        setTimeout(() => setThinking(""), 2000);
      }
    }, 3000);
    return () => clearInterval(interval);
  }, []);
  
  return { stream, thinking, currentTool };
};

export default function SharkCommandCenter() {
  const [emergencyMode, setEmergencyMode] = useState(false);
  const [overrideActive, setOverrideActive] = useState(false);
  const [showCommandPalette, setShowCommandPalette] = useState(false);
  const [cmdInput, setCmdInput] = useState("");
  const [tokens, setTokens] = useState(154200);
  const [tokenHistory, setTokenHistory] = useState([]);
  const [terminalLogs, setLogs] = useState([
    { t: "14:20:01", m: "System boot sequence complete.", type: "info" },
    { t: "14:20:05", m: "Sonar array synchronized.", type: "info" }
  ]);
  const [activeAgents, setActiveAgents] = useState([
    { id: 1, name: "CODER", status: "idle", task: null, progress: 0 },
    { id: 2, name: "REVIEWER", status: "idle", task: null, progress: 0 }
  ]);
  const [showThinking, setShowThinking] = useState(true);
  const [costPerHour, setCostPerHour] = useState(0.12);
  
  const { thinking, currentTool } = useAgentStream();
  const tokenRef = useRef(null);

  // Command Listener (CMD+K)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setShowCommandPalette(prev => !prev);
      }
      if (e.key === 'Escape') setShowCommandPalette(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Token tracking with history
  useEffect(() => {
    const iv = setInterval(() => {
      if (!emergencyMode) {
        const increment = Math.floor(Math.random() * 60);
        setTokens(t => {
          const newVal = t + increment;
          setTokenHistory(prev => [...prev.slice(-20), { time: Date.now(), tokens: newVal }]);
          return newVal;
        });
        
        // Visual feedback
        if (tokenRef.current && increment > 30) {
          const flash = document.createElement('div');
          flash.className = 'token-flash';
          flash.textContent = `+${increment}`;
          flash.style.left = `${Math.random() * 100}%`;
          flash.style.top = '0';
          tokenRef.current.appendChild(flash);
          setTimeout(() => flash.remove(), 1000);
        }
      }
    }, 2000);
    return () => clearInterval(iv);
  }, [emergencyMode]);

  const addLog = useCallback((m, type = "info") => {
    const time = new Date().toLocaleTimeString('en-GB', { hour12: false });
    setLogs(prev => [...prev.slice(-6), { t: time, m, type }]);
  }, []);

  const spawnAgent = (type) => {
    const newAgent = {
      id: Date.now(),
      name: type,
      status: "running",
      task: "Processing...",
      progress: 0
    };
    setActiveAgents(prev => [...prev, newAgent]);
    
    // Simulate progress
    let prog = 0;
    const interval = setInterval(() => {
      prog += 10;
      setActiveAgents(prev => prev.map(a => a.id === newAgent.id ? { ...a, progress: prog } : a));
      if (prog >= 100) {
        clearInterval(interval);
        setActiveAgents(prev => prev.filter(a => a.id !== newAgent.id));
        addLog(`Agent ${type} completed task`, "success");
      }
    }, 500);
  };

  const handleCommand = (e) => {
    if (e.key === 'Enter') {
      const cmd = cmdInput.toLowerCase().trim();
      addLog(`EXE: ${cmd}`, "command");
      
      if (cmd === '/abort' || cmd === '/stop') {
        setEmergencyMode(true);
        addLog("CRITICAL: EMERGENCY STOP TRIGGERED", "error");
      } else if (cmd === '/resume' || cmd === '/start') {
        setEmergencyMode(false);
        addLog("STATUS: SYSTEM RESUMED", "success");
      } else if (cmd === '/override') {
        setOverrideActive(prev => !prev);
        addLog(`STATUS: OVERRIDE ${!overrideActive ? 'ENABLED' : 'DISABLED'}`, "warning");
      } else if (cmd === '/spawn coder') {
        spawnAgent("CODER");
      } else if (cmd === '/spawn reviewer') {
        spawnAgent("REVIEWER");
      } else if (cmd === '/clear') {
        setLogs([]);
      } else {
        addLog(`ERR: COMMAND '${cmd}' NOT RECOGNIZED`, "error");
      }
      setCmdInput("");
      setShowCommandPalette(false);
    }
  };

  return (
    <div style={{ 
      minHeight: "100vh", color: "#e2e8f0", padding: "20px",
      fontFamily: "'Inter', sans-serif",
      animation: emergencyMode ? "emergencyPulse 2s infinite" : "none"
    }}>
      <style>{CSS}</style>
      <div className="ocean-bg">
        <div className="sonar-ring" />
        <div className="sonar-ring" style={{ animationDelay: "1.5s" }} />
      </div>

      {/* ── COMMAND PALETTE MODAL ── */}
      {showCommandPalette && (
        <div style={{
          position: "fixed", top: "50%", left: "50%", zIndex: 1000,
          width: "600px", background: "rgba(8,22,42,0.98)", backdropFilter: "blur(30px)",
          border: "1px solid #60a5fa55", borderRadius: "16px", 
          animation: "slideIn 0.2s ease-out", boxShadow: "0 25px 70px rgba(0,0,0,0.8)"
        }}>
          <div style={{ padding: "16px", background: "rgba(0,0,0,0.3)", borderBottom: "1px solid #ffffff11", display: "flex", gap: "12px", alignItems: "center" }}>
            <span style={{ color: "#60a5fa", fontFamily: "'JetBrains Mono'" }}>⌘K</span>
            <input 
              autoFocus value={cmdInput} 
              onChange={(e) => setCmdInput(e.target.value)} 
              onKeyDown={handleCommand}
              placeholder="Type a command... (/abort, /resume, /override, /spawn coder)"
              style={{ flex: 1, background: "transparent", border: "none", outline: "none", color: "#fff", fontSize: "14px", fontFamily: "'JetBrains Mono'" }} 
            />
          </div>
          <div style={{ padding: "8px", maxHeight: "300px", overflow: "auto" }}>
            {[
              { cmd: "/deploy", desc: "Release agent instance", color: "#4ade80" },
              { cmd: "/spawn coder", desc: "Spawn coding agent", color: "#60a5fa" },
              { cmd: "/spawn reviewer", desc: "Spawn code reviewer", color: "#a78bfa" },
              { cmd: "/override", desc: "Toggle manual control", color: "#fbbf24" },
              { cmd: "/abort", desc: "Emergency shutdown", color: "#f87171" },
              { cmd: "/clear", desc: "Clear terminal", color: "#94a3b8" },
            ].map((item, i) => (
              <div key={i} style={{ padding: "10px 16px", display: "flex", gap: "12px", borderRadius: "6px", cursor: "pointer", hover: { background: "rgba(255,255,255,0.05)" } }}>
                <span style={{ color: item.color, fontFamily: "'JetBrains Mono'", width: "120px" }}>{item.cmd}</span>
                <span style={{ color: "#64748b", fontSize: "12px" }}>{item.desc}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── HEADER ── */}
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: "28px", fontWeight: 800, color: emergencyMode ? "#f87171" : "#fff", letterSpacing: "-0.02em" }}>
            DWEEPBOT <span style={{ opacity: 0.4, fontWeight: 400 }}>// DEEPSEEK_V3</span>
          </h1>
          <div style={{ display: "flex", gap: "8px", marginTop: "12px" }}>
            {[
              { label: "AUTONOMY", status: "green", icon: "🦈" },
              { label: "WEB_SEARCH", status: "green", icon: "🌐" },
              { label: "CODE_EXEC", status: "green", icon: "⚡" },
              { label: "MEMORY", status: "yellow", icon: "🧠" },
            ].map((alert, i) => (
              <div key={i} style={{
                display: "flex", alignItems: "center", gap: "6px", padding: "4px 12px", borderRadius: "20px",
                background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)"
              }}>
                <span style={{ fontSize: "12px" }}>{alert.icon}</span>
                <span style={{ fontSize: "10px", fontFamily: "'JetBrains Mono'", color: alert.status === "red" ? "#f87171" : "#4ade80", fontWeight: 600 }}>{alert.label}</span>
              </div>
            ))}
          </div>
        </div>

        <div style={{ animation: emergencyMode ? "none" : "sharkProwl 6s ease-in-out infinite", filter: emergencyMode ? "grayscale(100%) brightness(0.5)" : "none" }}>
          <SharkLogo size={110} emergencyMode={emergencyMode} intensity={activeAgents.length} />
        </div>

        <div style={{ textAlign: "right" }}>
          <div ref={tokenRef} style={{ position: "relative", color: "#4ade80", fontSize: "24px", fontFamily: "'JetBrains Mono'", fontWeight: 700 }}>
            {tokens.toLocaleString()} <span style={{ fontSize: "12px", opacity: 0.6 }}>TKN</span>
          </div>
          <div style={{ fontSize: "11px", color: "#64748b", marginTop: "4px" }}>${costPerHour}/hr burn rate</div>
          <div style={{ fontSize: "10px", opacity: 0.4, fontFamily: "'JetBrains Mono'", marginTop: "4px" }}>
            DEPTH: 2,400M // AGENTS: {activeAgents.length}
          </div>
        </div>
      </header>

      {/* ── TOKEN BURN CHART ── */}
      <div className="dw-panel" style={{ padding: "16px", marginBottom: "16px", height: "120px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
          <span style={{ fontSize: "11px", color: "#64748b", fontFamily: "'JetBrains Mono'" }}>TOKEN_VELOCITY</span>
          <span style={{ fontSize: "10px", color: "#4ade80" }}>+12% vs last hour</span>
        </div>
        <ResponsiveContainer width="100%" height="80%">
          <LineChart data={tokenHistory}>
            <XAxis dataKey="time" hide />
            <YAxis hide domain={['dataMin', 'dataMax']} />
            <Tooltip 
              contentStyle={{ background: 'rgba(4,12,24,0.9)', border: '1px solid #334155', borderRadius: '8px' }}
              itemStyle={{ color: '#4ade80', fontSize: '11px' }}
            />
            <Line type="monotone" dataKey="tokens" stroke="#4ade80" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* ── EMERGENCY CONTROLS & AGENT SPAWN ── */}
      <div style={{ display: "flex", gap: "12px", marginBottom: "16px" }}>
        <button onClick={() => { setEmergencyMode(!emergencyMode); addLog("TOGGLE: E-STOP"); }} style={{
          flex: 1, background: emergencyMode ? "#dc2626" : "rgba(220,38,38,0.1)",
          border: `1px solid ${emergencyMode ? "#f87171" : "#dc262666"}`,
          color: emergencyMode ? "#fff" : "#f87171", padding: "14px", borderRadius: "12px",
          fontSize: "11px", fontFamily: "'JetBrains Mono'", fontWeight: 700, cursor: "pointer",
          transition: "all 0.2s"
        }}>
          ⚡ {emergencyMode ? "EMERGENCY STOPPED" : "E-STOP"}
        </button>
        <button onClick={() => { setOverrideActive(!overrideActive); addLog("TOGGLE: OVERRIDE"); }} style={{
          flex: 1, background: overrideActive ? "#0ea5e9" : "rgba(14,165,233,0.1)",
          border: `1px solid ${overrideActive ? "#38bdf8" : "#0ea5e966"}`,
          color: overrideActive ? "#fff" : "#38bdf8", padding: "14px", borderRadius: "12px",
          fontSize: "11px", fontFamily: "'JetBrains Mono'", fontWeight: 700, cursor: "pointer"
        }}>
          🎮 {overrideActive ? "MANUAL CONTROL" : "OVERRIDE"}
        </button>
        <button onClick={() => spawnAgent("CODER")} style={{
          flex: 1, background: "rgba(168,85,247,0.1)", border: "1px solid rgba(168,85,247,0.4)",
          color: "#c084fc", padding: "14px", borderRadius: "12px", fontSize: "11px", 
          fontFamily: "'JetBrains Mono'", cursor: "pointer", fontWeight: 700
        }}>
          👨‍💻 SPAWN CODER
        </button>
      </div>

      {/* ── ACTIVE AGENTS ── */}
      {activeAgents.length > 0 && (
        <div style={{ marginBottom: "16px" }}>
          <div style={{ fontSize: "10px", color: "#64748b", marginBottom: "8px", fontFamily: "'JetBrains Mono'" }}>ACTIVE_SWARM</div>
          <div style={{ display: "flex", gap: "12px" }}>
            {activeAgents.map(agent => (
              <div key={agent.id} className="dw-panel tool-execution" style={{ 
                flex: 1, padding: "12px", borderLeft: "3px solid #60a5fa",
                display: "flex", alignItems: "center", gap: "12px"
              }}>
                <div style={{ 
                  width: "32px", height: "32px", borderRadius: "50%", 
                  background: "linear-gradient(135deg, #60a5fa, #3b82f6)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: "14px"
                }}>
                  {agent.name === "CODER" ? "💻" : "🔍"}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: "12px", fontWeight: 600, color: "#fff" }}>{agent.name}</div>
                  <div style={{ fontSize: "10px", color: "#64748b" }}>{agent.task}</div>
                  <div style={{ 
                    height: "3px", background: "rgba(255,255,255,0.1)", borderRadius: "2px", marginTop: "6px" 
                  }}>
                    <div style={{ 
                      height: "100%", width: `${agent.progress}%`, background: "#60a5fa", borderRadius: "2px",
                      transition: "width 0.3s ease"
                    }} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── THINKING STREAM ── */}
      {showThinking && thinking && (
        <div className="dw-panel" style={{ padding: "16px", marginBottom: "16px", borderLeft: "3px solid #fbbf24" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <span style={{ fontSize: "10px", color: "#fbbf24", fontFamily: "'JetBrains Mono'" }}>🧠 DEEPSEEK_THINKING</span>
            <span style={{ animation: "thinkingPulse 1.5s infinite", color: "#fbbf24", fontSize: "10px" }}>●</span>
          </div>
          <div className="thinking-stream">{thinking}</div>
        </div>
      )}

      {/* ── GRID SYSTEM ── */}
      <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr 1fr", gap: "16px" }}>
        
        {/* MISSION BRIEFING */}
        <div className="dw-panel" style={{ padding: "16px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
            <h3 style={{ margin: 0, fontSize: "13px", color: "#a0d2f0", fontWeight: 600 }}>MISSION: AUTONOMOUS_LOOP</h3>
            <span style={{ fontSize: "9px", fontFamily: "'JetBrains Mono'", color: "#00e5ff", animation: "thinkingPulse 1.8s ease infinite" }}>● ACTIVE</span>
          </div>
          
          <div style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
            {["PLAN", "ACT", "OBSERVE", "REFLECT"].map((phase, i) => (
              <div key={i} style={{ 
                flex: 1, padding: "8px", textAlign: "center", borderRadius: "6px",
                background: i === 1 ? "rgba(96,165,250,0.2)" : "rgba(255,255,255,0.03)",
                border: i === 1 ? "1px solid #60a5fa" : "1px solid transparent",
                fontSize: "10px", fontFamily: "'JetBrains Mono'",
                color: i === 1 ? "#60a5fa" : "#64748b"
              }}>
                {phase}
              </div>
            ))}
          </div>

          {[
            { task: "Analyze codebase structure", status: "done", time: "2.3s" },
            { task: "Generate implementation plan", status: "active", time: "..." },
            { task: "Execute file modifications", status: "pending", time: "--" }
          ].map((item, i) => (
            <div key={i} style={{ 
              padding: "10px", background: "rgba(255,255,255,0.03)", borderRadius: "8px", 
              marginBottom: "8px", fontSize: "12px", display: "flex", justifyContent: "space-between",
              alignItems: "center", borderLeft: item.status === 'active' ? "2px solid #60a5fa" : "2px solid transparent"
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ 
                  width: "6px", height: "6px", borderRadius: "50%",
                  background: item.status === 'done' ? "#4ade80" : item.status === 'active' ? "#60a5fa" : "#64748b"
                }} />
                <span style={{ opacity: item.status === 'pending' ? 0.5 : 1 }}>{item.task}</span>
              </div>
              <span style={{ color: "#64748b", fontSize: "10px", fontFamily: "'JetBrains Mono'" }}>{item.time}</span>
            </div>
          ))}

          {/* Personality Sliders */}
          <div style={{ marginTop: "20px", padding: "12px", borderRadius: "8px", background: "rgba(255,255,255,.03)" }}>
            <div style={{ fontSize: "9px", color: "#60a5fa", fontFamily: "'JetBrains Mono'", fontWeight: 700, marginBottom: "12px" }}>PERSONALITY_MODULATION</div>
            {[
              {l:"REASONING_DEPTH", v:85, c:"#c084fc"}, 
              {l:"CODE_QUALITY", v:92, c:"#60a5fa"},
              {l:"EXPLORATION", v:45, c:"#4ade80"}
            ].map((s, i) => (
              <div key={i} style={{ marginBottom: "10px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "9px", marginBottom: "4px" }}>
                  <span style={{ color: s.c }}>{s.l}</span> 
                  <span style={{ color: "#4a6a8a" }}>{s.v}%</span>
                </div>
                <div style={{ height: "4px", background: "rgba(255,255,255,.06)", borderRadius: "4px" }}>
                  <div style={{ height: "100%", width: `${s.v}%`, background: s.c, borderRadius: "4px", transition: "width 0.3s" }}/>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* CONTEXT & MEMORY */}
        <div className="dw-panel" style={{ padding: "16px", display: "flex", flexDirection: "column" }}>
          <div style={{ fontSize: "9px", color: "#4a6a8a", fontFamily: "'JetBrains Mono'", marginBottom: "12px" }}>CONTEXT_WINDOW</div>
          
          <div style={{ 
            padding: "12px", background: "rgba(0,0,0,0.3)", borderRadius: "8px", marginBottom: "12px",
            border: "1px solid rgba(96,165,250,0.2)"
          }}>
            <div style={{ fontSize: "10px", color: "#60a5fa", marginBottom: "4px" }}>CURRENT_FILE</div>
            <div style={{ fontSize: "11px", color: "#e2e8f0", fontFamily: "'JetBrains Mono'" }}>src/agents/coder.py</div>
            <div style={{ fontSize: "9px", color: "#64748b", marginTop: "4px" }}>Lines 45-89 selected</div>
          </div>

          <div style={{ marginBottom: "12px" }}>
            <div style={{ fontSize: "9px", color: "#4a6a8a", marginBottom: "8px" }}>RECENT_CONTEXT</div>
            {[
              "Refactoring auth middleware",
              "Added JWT validation",
              "Fixed token expiry bug"
            ].map((ctx, i) => (
              <div key={i} style={{ 
                padding: "6px 8px", fontSize: "11px", color: "#94a3b8",
                borderLeft: "2px solid #334155", paddingLeft: "8px", marginBottom: "4px"
              }}>
                {ctx}
              </div>
            ))}
          </div>

          <div style={{ marginTop: "auto", borderTop: "1px solid #ffffff11", paddingTop: "12px" }}>
            <div style={{ fontSize: "9px", color: "#4a6a8a", marginBottom: "8px" }}>MEMORY_STACK</div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", marginBottom: "4px" }}>
              <span style={{ color: "#64748b" }}>WORKING</span>
              <span style={{ color: "#4ade80" }}>1.2GB / 2GB</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px" }}>
              <span style={{ color: "#64748b" }}>VECTOR_DB</span>
              <span style={{ color: "#60a5fa" }}>44.8GB</span>
            </div>
          </div>
        </div>

        {/* LOG TERMINAL */}
        <div className="dw-panel" style={{ padding: "16px", background: "rgba(0,0,0,0.4)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
            <span style={{ fontSize: "9px", color: "#22c55e", fontFamily: "'JetBrains Mono'" }}>TERMINAL_OUTPUT</span>
            <button onClick={() => setLogs([])} style={{ 
              fontSize: "9px", color: "#64748b", background: "none", border: "none", cursor: "pointer" 
            }}>CLEAR</button>
          </div>
          <div style={{ fontSize: "11px", fontFamily: "'JetBrains Mono'", lineHeight: "1.5", maxHeight: "300px", overflow: "auto" }}>
            {terminalLogs.map((log, i) => (
              <div key={i} style={{ marginBottom: "4px", animation: "slideIn 0.2s ease-out" }}>
                <span style={{ opacity: 0.3 }}>[{log.t}]</span>{' '}
                <span style={{ 
                  color: log.type === 'error' ? '#f87171' : log.type === 'success' ? '#4ade80' : log.type === 'warning' ? '#fbbf24' : log.type === 'command' ? '#60a5fa' : '#e2e8f0',
                  fontWeight: log.type === 'command' ? 600 : 400
                }}>{log.m}</span>
              </div>
            ))}
            <div style={{ 
              display: "inline-block", width: "8px", height: "14px", background: "#4ade80", 
              marginLeft: "2px", animation: "thinkingPulse 1s infinite", verticalAlign: "middle" 
            }} />
          </div>
        </div>

      </div>

      {/* ── FOOTER ── */}
      <footer style={{ 
        marginTop: "24px", paddingTop: "16px", borderTop: "1px solid rgba(255,255,255,0.1)",
        display: "flex", justifyContent: "space-between", fontSize: "10px", color: "#475569"
      }}>
        <div>DWEEPBOT v2.0.1 // DEEPSEEK-V3 API</div>
        <div style={{ display: "flex", gap: "16px" }}>
          <span>LATENCY: 45ms</span>
          <span>UPTIME: 4d 12h 33m</span>
        </div>
      </footer>
    </div>
  );
}
